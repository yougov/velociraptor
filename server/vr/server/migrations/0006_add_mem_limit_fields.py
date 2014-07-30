# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Release.mem_limit'
        db.add_column('deployment_release', 'mem_limit',
                      self.gf('django.db.models.fields.CharField')(max_length=32, null=True),
                      keep_default=False)

        # Adding field 'Release.memsw_limit'
        db.add_column('deployment_release', 'memsw_limit',
                      self.gf('django.db.models.fields.CharField')(max_length=32, null=True),
                      keep_default=False)

        # Adding field 'Swarm.mem_limit'
        db.add_column('deployment_swarm', 'mem_limit',
                      self.gf('django.db.models.fields.CharField')(max_length=32, null=True),
                      keep_default=False)

        # Adding field 'Swarm.memsw_limit'
        db.add_column('deployment_swarm', 'memsw_limit',
                      self.gf('django.db.models.fields.CharField')(max_length=32, null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Release.mem_limit'
        db.delete_column('deployment_release', 'mem_limit')

        # Deleting field 'Release.memsw_limit'
        db.delete_column('deployment_release', 'memsw_limit')

        # Deleting field 'Swarm.mem_limit'
        db.delete_column('deployment_swarm', 'mem_limit')

        # Deleting field 'Swarm.memsw_limit'
        db.delete_column('deployment_swarm', 'memsw_limit')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'server.app': {
            'Meta': {'ordering': "('name',)", 'object_name': 'App', 'db_table': "'deployment_app'"},
            'buildpack': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['server.BuildPack']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'repo_url': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'server.build': {
            'Meta': {'ordering': "['-id']", 'object_name': 'Build', 'db_table': "'deployment_build'"},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['server.App']"}),
            'buildpack_url': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'buildpack_version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'compile_log': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'env_yaml': ('vr.server.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '20'}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'server.buildpack': {
            'Meta': {'ordering': "['order']", 'object_name': 'BuildPack', 'db_table': "'deployment_buildpack'"},
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'git'", 'max_length': '10'}),
            'repo_url': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        'server.configingredient': {
            'Meta': {'ordering': "['name']", 'object_name': 'ConfigIngredient', 'db_table': "'deployment_configingredient'"},
            'config_yaml': ('vr.server.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'env_yaml': ('vr.server.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        'server.deploymentlogentry': {
            'Meta': {'ordering': "['-time']", 'object_name': 'DeploymentLogEntry', 'db_table': "'deployment_deploymentlogentry'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'server.host': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Host', 'db_table': "'deployment_host'"},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'squad': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'hosts'", 'null': 'True', 'to': "orm['server.Squad']"})
        },
        'server.portlock': {
            'Meta': {'unique_together': "(('host', 'port'),)", 'object_name': 'PortLock', 'db_table': "'deployment_portlock'"},
            'created_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['server.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {})
        },
        'server.release': {
            'Meta': {'ordering': "['-id']", 'object_name': 'Release', 'db_table': "'deployment_release'"},
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['server.Build']"}),
            'config_yaml': ('vr.server.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'env_yaml': ('vr.server.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mem_limit': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'memsw_limit': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'run_as': ('django.db.models.fields.CharField', [], {'default': "'nobody'", 'max_length': '32'}),
            'volumes': ('vr.server.fields.YAMLListField', [], {'null': 'True', 'blank': 'True'})
        },
        'server.squad': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Squad', 'db_table': "'deployment_squad'"},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        'server.swarm': {
            'Meta': {'ordering': "['app__name', 'config_name', 'proc_name']", 'unique_together': "(('app', 'config_name', 'squad', 'proc_name'),)", 'object_name': 'Swarm', 'db_table': "'deployment_swarm'"},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['server.App']", 'null': 'True'}),
            'balancer': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'config_ingredients': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['server.ConfigIngredient']", 'symmetrical': 'False', 'blank': 'True'}),
            'config_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'config_yaml': ('vr.server.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'env_yaml': ('vr.server.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mem_limit': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'memsw_limit': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True'}),
            'pool': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'proc_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['server.Release']"}),
            'run_as': ('django.db.models.fields.CharField', [], {'default': "'nobody'", 'max_length': '32'}),
            'size': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'squad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['server.Squad']"}),
            'volumes': ('vr.server.fields.YAMLListField', [], {'null': 'True', 'blank': 'True'})
        },
        'server.tag': {
            'Meta': {'object_name': 'Tag', 'db_table': "'deployment_tag'"},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['server.App']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'server.testresult': {
            'Meta': {'object_name': 'TestResult', 'db_table': "'deployment_testresult'"},
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'procname': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'results': ('django.db.models.fields.TextField', [], {}),
            'run': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tests'", 'to': "orm['server.TestRun']"}),
            'testcount': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time': ('django.db.models.fields.DateTimeField', [], {})
        },
        'server.testrun': {
            'Meta': {'ordering': "['-start']", 'object_name': 'TestRun', 'db_table': "'deployment_testrun'"},
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        }
    }

    complete_apps = ['server']