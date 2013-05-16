# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'ConfigIngredient.env_yaml'
        db.alter_column('deployment_configingredient', 'env_yaml', self.gf('vr.deployment.fields.YAMLDictField')(null=True))

        # Changing field 'ConfigIngredient.config_yaml'
        db.alter_column('deployment_configingredient', 'config_yaml', self.gf('vr.deployment.fields.YAMLDictField')(null=True))
        # Adding field 'Build.hash'
        db.add_column('deployment_build', 'hash',
                      self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True),
                      keep_default=False)


    def backwards(self, orm):

        # Changing field 'ConfigIngredient.env_yaml'
        db.alter_column('deployment_configingredient', 'env_yaml', self.gf('vr.deployment.fields.YAMLDictField')(default=''))

        # Changing field 'ConfigIngredient.config_yaml'
        db.alter_column('deployment_configingredient', 'config_yaml', self.gf('vr.deployment.fields.YAMLDictField')(default=''))
        # Deleting field 'Build.hash'
        db.delete_column('deployment_build', 'hash')


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
        'deployment.app': {
            'Meta': {'ordering': "('name',)", 'object_name': 'App'},
            'buildpack': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.BuildPack']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'repo_type': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'repo_url': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'deployment.build': {
            'Meta': {'ordering': "['-id']", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.App']"}),
            'buildpack_url': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
            'buildpack_version': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'env_yaml': ('vr.deployment.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '20'}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'deployment.buildpack': {
            'Meta': {'ordering': "['order']", 'object_name': 'BuildPack'},
            'desc': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {}),
            'repo_type': ('django.db.models.fields.CharField', [], {'default': "'git'", 'max_length': '10'}),
            'repo_url': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        'deployment.configingredient': {
            'Meta': {'ordering': "['name']", 'object_name': 'ConfigIngredient'},
            'config_yaml': ('vr.deployment.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'env_yaml': ('vr.deployment.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        'deployment.deploymentlogentry': {
            'Meta': {'ordering': "['-time']", 'object_name': 'DeploymentLogEntry'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.TextField', [], {}),
            'time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'deployment.host': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Host'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'squad': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'hosts'", 'null': 'True', 'to': "orm['deployment.Squad']"})
        },
        'deployment.portlock': {
            'Meta': {'unique_together': "(('host', 'port'),)", 'object_name': 'PortLock'},
            'created_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Host']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {})
        },
        'deployment.release': {
            'Meta': {'ordering': "['-id']", 'object_name': 'Release'},
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Build']"}),
            'config_yaml': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'env_yaml': ('vr.deployment.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'deployment.squad': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Squad'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        'deployment.swarm': {
            'Meta': {'ordering': "['app__name', 'config_name', 'proc_name']", 'unique_together': "(('app', 'squad', 'proc_name'),)", 'object_name': 'Swarm'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.App']", 'null': 'True'}),
            'balancer': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'config_ingredients': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['deployment.ConfigIngredient']", 'symmetrical': 'False', 'blank': 'True'}),
            'config_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'config_yaml': ('vr.deployment.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'env_yaml': ('vr.deployment.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pool': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'proc_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Release']"}),
            'size': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'squad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Squad']"})
        },
        'deployment.tag': {
            'Meta': {'object_name': 'Tag'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.App']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'deployment.testresult': {
            'Meta': {'object_name': 'TestResult'},
            'hostname': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'passed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'procname': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'results': ('django.db.models.fields.TextField', [], {}),
            'run': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tests'", 'to': "orm['deployment.TestRun']"}),
            'testcount': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'time': ('django.db.models.fields.DateTimeField', [], {})
        },
        'deployment.testrun': {
            'Meta': {'ordering': "['-start']", 'object_name': 'TestRun'},
            'end': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        }
    }

    complete_apps = ['deployment']