import os

import suds.xsd.doctor
import suds.client
from suds.plugin import MessagePlugin


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
# has add_nodes and delete_nodes functions, and can be initted with a
# dictionary of config that can be pulled from settings.BALANCERS.
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

    def add_nodes(self, pool, nodes):
        wrapper = self.client.factory.create('StringArrayArray')
        nodes_array = self.client.factory.create('StringArray')
        nodes_array.item = [nodes]
        wrapper.item = [nodes_array]
        self.client.service.addNodes([self.pool_prefix + pool], wrapper)

    def delete_nodes(self, pool, nodes):
        wrapper = self.client.factory.create('StringArrayArray')
        nodes_array = self.client.factory.create('StringArray')
        nodes_array.item = [nodes]
        wrapper.item = [nodes_array]
        self.client.service.removeNodes([self.pool_prefix + pool], wrapper)

    def get_nodes(self, pool):
        nodes = self.client.service.getNodes([self.pool_prefix + pool])[0]
        # TODO: convert the sax text things into real strings
        return [str(n) for n in nodes]

