"""
Code adapted from supervisor.childutils and supervisor.xmlrpc so we don't have
to include all of Supervisor as a dependency for this library.
"""
import sys
import xmlrpclib
import urllib
import httplib
import socket


class UnixStreamHTTPConnection(httplib.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # we abuse the host parameter as the socketname
        self.sock.connect(self.socketfile)


class SupervisorTransport(xmlrpclib.Transport):
    """
    Provides a Transport for xmlrpclib that uses
    httplib.HTTPConnection in order to support persistent
    connections.  Also support basic auth and UNIX domain socket
    servers.
    """
    connection = None

    _use_datetime = 0 # python 2.5 fwd compatibility
    def __init__(self, username=None, password=None, serverurl=None):
        self.username = username
        self.password = password
        self.verbose = False
        self.serverurl = serverurl
        if serverurl.startswith('http://'):
            type, uri = urllib.splittype(serverurl)
            host, path = urllib.splithost(uri)
            host, port = urllib.splitport(host)
            if port is None:
                port = 80
            else:
                port = int(port)
            def get_connection(host=host, port=port):
                return httplib.HTTPConnection(host, port)
            self._get_connection = get_connection
        elif serverurl.startswith('unix://'):
            def get_connection(serverurl=serverurl):
                # we use 'localhost' here because domain names must be
                # < 64 chars (or we'd use the serverurl filename)
                conn = UnixStreamHTTPConnection('localhost')
                conn.socketfile = serverurl[7:]
                return conn
            self._get_connection = get_connection
        else:
            raise ValueError('Unknown protocol for serverurl %s' % serverurl)

    def request(self, host, handler, request_body, verbose=0):
        if not self.connection:
            self.connection = self._get_connection()
            self.headers = {
                "User-Agent" : self.user_agent,
                "Content-Type" : "text/xml",
                "Accept": "text/xml"
                }

            # basic auth
            if self.username is not None and self.password is not None:
                unencoded = "%s:%s" % (self.username, self.password)
                encoded = unencoded.encode('base64')
                encoded = encoded.replace('\012', '')
                self.headers["Authorization"] = "Basic %s" % encoded

        self.headers["Content-Length"] = str(len(request_body))

        self.connection.request('POST', handler, request_body, self.headers)

        r = self.connection.getresponse()

        if r.status != 200:
            self.connection.close()
            self.connection = None
            raise xmlrpclib.ProtocolError(host + handler,
                                          r.status,
                                          r.reason,
                                          '' )
        data = r.read()
        p, u = self.getparser()
        p.feed(data)
        p.close()
        return u.close()


def getRPCTransport(env):
    u = env.get('SUPERVISOR_USERNAME', '')
    p = env.get('SUPERVISOR_PASSWORD', '')
    return SupervisorTransport(u, p, env['SUPERVISOR_SERVER_URL'])


def getRPCInterface(env):
    # dumbass ServerProxy won't allow us to pass in a non-HTTP url,
    # so we fake the url we pass into it and always use the transport's
    # 'serverurl' to figure out what to attach to
    return xmlrpclib.ServerProxy('http://127.0.0.1', getRPCTransport(env))


def get_headers(line):
    return dict([ x.split(':') for x in line.split() ])


def eventdata(payload):
    headerinfo, data = payload.split('\n', 1)
    headers = get_headers(headerinfo)
    return headers, data

def compact_traceback():
    t, v, tb = sys.exc_info()
    tbinfo = []
    assert tb # Must have a traceback
    while tb:
        tbinfo.append((
            tb.tb_frame.f_code.co_filename,
            tb.tb_frame.f_code.co_name,
            str(tb.tb_lineno)
            ))
        tb = tb.tb_next

    # just to be safe
    del tb

    file, function, line = tbinfo[-1]
    info = ' '.join(['[%s|%s|%s]' % x for x in tbinfo])
    return (file, function, line), t, v, info


class PDispatcher:
    """ Asyncore dispatcher for mainloop, representing a process channel
    (stdin, stdout, or stderr).  This class is abstract. """

    closed = False # True if close() has been called

    def __repr__(self):
        return '<%s at %s for %s (%s)>' % (self.__class__.__name__,
                                           id(self),
                                           self.process,
                                           self.channel)

    def readable(self):
        raise NotImplementedError

    def writable(self):
        raise NotImplementedError

    def handle_read_event(self):
        raise NotImplementedError

    def handle_write_event(self):
        raise NotImplementedError

    def handle_error(self):
        nil, t, v, tbinfo = compact_traceback()

        self.process.config.options.logger.critical(
            'uncaptured python exception, closing channel %s (%s:%s %s)' % (
                repr(self),
                t,
                v,
                tbinfo
                )
            )
        self.close()

    def close(self):
        if not self.closed:
            self.process.config.options.logger.debug(
                'fd %s closed, stopped monitoring %s' % (self.fd, self))
            self.closed = True

    def flush(self):
        pass


class EventListenerStates:
    READY = 10 # the process ready to be sent an event from supervisor
    BUSY = 20 # event listener is processing an event sent to it by supervisor
    ACKNOWLEDGED = 30 # the event listener processed an event
    UNKNOWN = 40 # the event listener is in an unknown state

class LevelsByName:
    CRIT = 50   # messages that probably require immediate user attention
    ERRO = 40   # messages that indicate a potentially ignorable error condition
    WARN = 30   # messages that indicate issues which aren't errors
    INFO = 20   # normal informational output
    DEBG = 10   # messages useful for users trying to debug configurations
    TRAC = 5    # messages useful to developers trying to debug plugins
    BLAT = 3    # messages useful for developers trying to debug supervisor


ANSI_ESCAPE_BEGIN = '\x1b['
ANSI_TERMINATORS = ('H', 'f', 'A', 'B', 'C', 'D', 'R', 's', 'u', 'J',
                    'K', 'h', 'l', 'p', 'm')


def stripEscapes(string):
    """
    Remove all ANSI color escapes from the given string.
    """
    result = ''
    show = 1
    i = 0
    L = len(string)
    while i < L:
        if show == 0 and string[i] in ANSI_TERMINATORS:
            show = 1
        elif show:
            n = string.find(ANSI_ESCAPE_BEGIN, i)
            if n == -1:
                return result + string[i:]
            else:
                result = result + string[i:n]
                i = n
                show = 0
        i = i + 1
    return result


callbacks = []


def notify(event):
    for type, callback in callbacks:
        if isinstance(event, type):
            callback(event)


class EventRejectedEvent: # purposely does not subclass Event 
    def __init__(self, process, event):
        self.process = process
        self.event = event


class PEventListenerDispatcher(PDispatcher):
    """ An output dispatcher that monitors and changes a process'
    listener_state """
    process = None # process which "owns" this dispatcher
    channel = None # 'stderr' or 'stdout'
    childlog = None # the logger
    state_buffer = ''  # data waiting to be reviewed for state changes

    READY_FOR_EVENTS_TOKEN = 'READY\n'
    RESULT_TOKEN_START = 'RESULT '
    READY_FOR_EVENTS_LEN = len(READY_FOR_EVENTS_TOKEN)
    RESULT_TOKEN_START_LEN = len(RESULT_TOKEN_START)

    def __init__(self, process, channel, fd):
        self.process = process
        # the initial state of our listener is ACKNOWLEDGED; this is a
        # "busy" state that implies we're awaiting a READY_FOR_EVENTS_TOKEN
        self.process.listener_state = EventListenerStates.ACKNOWLEDGED
        self.process.event = None
        self.result = ''
        self.resultlen = None
        self.channel = channel
        self.fd = fd

        logfile = getattr(process.config, '%s_logfile' % channel)

        if logfile:
            maxbytes = getattr(process.config, '%s_logfile_maxbytes' % channel)
            backups = getattr(process.config, '%s_logfile_backups' % channel)
            self.childlog = process.config.options.getLogger(
                logfile,
                LevelsByName.INFO,
                '%(message)s',
                rotating=not not maxbytes, # optimization
                maxbytes=maxbytes,
                backups=backups)

    def removelogs(self):
        if self.childlog is not None:
            for handler in self.childlog.handlers:
                handler.remove()
                handler.reopen()

    def reopenlogs(self):
        if self.childlog is not None:
            for handler in self.childlog.handlers:
                handler.reopen()


    def writable(self):
        return False

    def readable(self):
        if self.closed:
            return False
        return True

    def handle_read_event(self):
        data = self.process.config.options.readfd(self.fd)
        if data:
            self.state_buffer += data
            procname = self.process.config.name
            msg = '%r %s output:\n%s' % (procname, self.channel, data)
            self.process.config.options.logger.debug(msg)

            if self.childlog:
                if self.process.config.options.strip_ansi:
                    data = stripEscapes(data)
                self.childlog.info(data)
        else:
            # if we get no data back from the pipe, it means that the
            # child process has ended.  See
            # mail.python.org/pipermail/python-dev/2004-August/046850.html
            self.close()

        self.handle_listener_state_change()

    def handle_listener_state_change(self):
        data = self.state_buffer

        if not data:
            return

        process = self.process
        procname = process.config.name
        state = process.listener_state

        if state == EventListenerStates.UNKNOWN:
            # this is a fatal state
            self.state_buffer = ''
            return

        if state == EventListenerStates.ACKNOWLEDGED:
            if len(data) < self.READY_FOR_EVENTS_LEN:
                # not enough info to make a decision
                return
            elif data.startswith(self.READY_FOR_EVENTS_TOKEN):
                msg = '%s: ACKNOWLEDGED -> READY' % procname
                process.config.options.logger.debug(msg)
                process.listener_state = EventListenerStates.READY
                tokenlen = self.READY_FOR_EVENTS_LEN
                self.state_buffer = self.state_buffer[tokenlen:]
                process.event = None
            else:
                msg = '%s: ACKNOWLEDGED -> UNKNOWN' % procname
                process.config.options.logger.debug(msg)
                process.listener_state = EventListenerStates.UNKNOWN
                self.state_buffer = ''
                process.event = None
            if self.state_buffer:
                # keep going til its too short
                self.handle_listener_state_change()
            else:
                return

        elif state == EventListenerStates.READY:
            # the process sent some spurious data, be a hardass about it
            msg = '%s: READY -> UNKNOWN' % procname
            process.config.options.logger.debug(msg)
            process.listener_state = EventListenerStates.UNKNOWN
            self.state_buffer = ''
            process.event = None
            return

        elif state == EventListenerStates.BUSY:
            if self.resultlen is None:
                # we haven't begun gathering result data yet
                pos = data.find('\n')
                if pos == -1:
                    # we can't make a determination yet, we dont have a full
                    # results line
                    return

                result_line = self.state_buffer[:pos]
                self.state_buffer = self.state_buffer[pos+1:] # rid LF
                resultlen = result_line[self.RESULT_TOKEN_START_LEN:]
                try:
                    self.resultlen = int(resultlen)
                except ValueError:
                    msg = ('%s: BUSY -> UNKNOWN (bad result line %r)'
                           % (procname, result_line))
                    process.config.options.logger.debug(msg)
                    process.listener_state = EventListenerStates.UNKNOWN
                    self.state_buffer = ''
                    notify(EventRejectedEvent(process, process.event))
                    process.event = None
                    return

            else:
                needed = self.resultlen - len(self.result)

                if needed:
                    self.result += self.state_buffer[:needed]
                    self.state_buffer = self.state_buffer[needed:]
                    needed = self.resultlen - len(self.result)

                if not needed:
                    self.handle_result(self.result)
                    self.process.event = None
                    self.result = ''
                    self.resultlen = None

            if self.state_buffer:
                # keep going til its too short
                self.handle_listener_state_change()
            else:
                return

    def handle_result(self, result):
        process = self.process
        procname = process.config.name

        try:
            self.process.group.config.result_handler(process.event, result)
            msg = '%s: BUSY -> ACKNOWLEDGED (processed)' % procname
            process.listener_state = EventListenerStates.ACKNOWLEDGED
        except RejectEvent:
            msg = '%s: BUSY -> ACKNOWLEDGED (rejected)' % procname
            process.listener_state = EventListenerStates.ACKNOWLEDGED
            notify(EventRejectedEvent(process, process.event))
        except:
            msg = '%s: BUSY -> UNKNOWN' % procname
            process.listener_state = EventListenerStates.UNKNOWN
            notify(EventRejectedEvent(process, process.event))

        process.config.options.logger.debug(msg)



class EventListenerProtocol:
    def wait(self, stdin=sys.stdin, stdout=sys.stdout):
        self.ready(stdout)
        line = stdin.readline()
        headers = get_headers(line)
        payload = stdin.read(int(headers['len']))
        return headers, payload

    def ready(self, stdout=sys.stdout):
        stdout.write(PEventListenerDispatcher.READY_FOR_EVENTS_TOKEN)
        stdout.flush()

    def ok(self, stdout=sys.stdout):
        self.send('OK', stdout)

    def fail(self, stdout=sys.stdout):
        self.send('FAIL', stdout)

    def send(self, data, stdout=sys.stdout):
        resultlen = len(data)
        result = '%s%s\n%s' % (PEventListenerDispatcher.RESULT_TOKEN_START,
                               str(resultlen),
                               data)
        stdout.write(result)
        stdout.flush()

class RejectEvent(Exception):
    """ The exception type expected by a dispatcher when a handler wants
    to reject an event """

listener = EventListenerProtocol()
