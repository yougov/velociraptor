import os

import suds.xsd.doctor
import suds.client
from suds.plugin import MessagePlugin
from suds import WebFault


# Suds has broken array marshaling.  See these links:
# http://stackoverflow.com/questions/3519818/suds-incorrect-marshaling-of-array-of-arrays
# https://fedorahosted.org/suds/ticket/340
class FixArrayPlugin(MessagePlugin):
    def marshalled(self, context):
        command = context.envelope.getChild('Body').getChildren()[0].name
        # TODO: instead of blacklisting the affected types here, check the
        # actual WSDL and fix up any *ArrayArray types.
        affected = ('addNodes',
                    'addDrainingNodes',
                    'removeNodes',
                    'removeDrainingNodes',
                    'disableNodes',
                    'enableNodes',
                   )
        if command in affected:
            context.envelope.addPrefix('xsd', 'http://www.w3.org/1999/XMLSchema')
            values = context.envelope.getChild('Body').getChild(command).getChild('values')
            values.set('SOAP-ENC:arrayType', 'xsd:list[1]')
            values.set('xsi:type', 'SOAP-ENC:Array')
            item = values[0]
            item.set('SOAP-ENC:arrayType', 'xsd:list[1]')
            item.set('xsi:type', 'SOAP-ENC:Array')


# This class implements velociraptor's Balancer Interface, which means that it
# has get_nodes, add_nodes, and delete_nodes functions, and is initted with a
# dictionary of config pulled from settings.BALANCERS.
class ZXTMBalancer(object):
    def __init__(self, config):
        self.url = config['URL']
        imp = suds.xsd.doctor.Import('http://schemas.xmlsoap.org/soap/encoding/')
        imp.filter.add('http://soap.zeus.com/zxtm/1.0/')
        doctor = suds.xsd.doctor.ImportDoctor(imp)

        # zxtm_pool.wsdl must be present in the same directory as this file.
        here = os.path.dirname(os.path.realpath(__file__))
        wsdl = os.path.join(here, 'zxtm_pool.wsdl')
        self.client = suds.client.Client(
            'file:' + wsdl,
            username=config['USER'], password=config['PASSWORD'],
            location=self.url, plugins=[doctor, FixArrayPlugin()])

        # All pool names will be prefixed with this string.
        self.pool_prefix = config.get('POOL_PREFIX', '')

    def _call_node_func(self, func, pool, nodes):
        # Generic function for calling any of the ZXTM pool functions that
        # accept an array of pools, and an arrayarray of nodes.  This function
        # will take a single pool and nodelist and do all the necessary
        # wrapping.
        nodes_wrapper = self.client.factory.create('StringArrayArray')
        nodes_array = self.client.factory.create('StringArray')
        nodes_array.item = [nodes]
        nodes_wrapper.item = [nodes_array]
        func([self.pool_prefix + pool], nodes_wrapper)

    def add_nodes(self, pool, nodes):
        # ZXTM will kindly avoid creating duplicates if you submit a node more
        # than once.
        try:
            self._call_node_func(self.client.service.addNodes, pool, nodes)
        except WebFault:
            # If pool doesn't exist, create it.
            # TODO: filter on WebFault message, so we only try addPool if the
            # failure was from "no such pool", else re-raise the exception.
            self._call_node_func(self.client.service.addPool, pool, nodes)

    def delete_nodes(self, pool, nodes):
        # will raise WebFault if node doesn't exist.
        try:
            self._call_node_func(self.client.service.removeNodes, pool, nodes)
        except WebFault:
            pass
            # TODO: filter on message, and re-raise if it isn't the "node does
            # not exist" message that we're expecting.

    def get_nodes(self, pool):
        try:
            # get just the first item from the arrayarray
            nodes = self.client.service.getNodes([self.pool_prefix + pool])[0]
            # convert the sax text things into real strings
            return [str(n) for n in nodes]
        except WebFault:
            # TODO: filter on WebFault message so we can re-raise anything but
            # "pool does not exist"
            return []

