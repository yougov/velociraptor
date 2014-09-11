import xmlrpclib

import supervisor.xmlrpc


def xmlrpc_marshal(value):
    ismethodresponse = not isinstance(value, xmlrpclib.Fault)
    if ismethodresponse:
        if not isinstance(value, tuple):
            value = (value,)
        body = xmlrpclib.dumps(value,  methodresponse=ismethodresponse,
                               allow_none=True)
    else:
        body = xmlrpclib.dumps(value, allow_none=True)
    return body

# monkeypatch supervisor XML-RPC code to permit None values in responses
supervisor.xmlrpc.xmlrpc_marshal = xmlrpc_marshal
