# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Deleting field 'Swarm.automate'
        db.delete_column('deployment_swarm', 'automate')

        # Adding field 'Swarm.active'
        db.add_column('deployment_swarm', 'active', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)


    def backwards(self, orm):
        
        # Adding field 'Swarm.automate'
        db.add_column('deployment_swarm', 'automate', self.gf('django.db.models.fields.BooleanField')(default=False), keep_default=False)

        # Deleting field 'Swarm.active'
        db.delete_column('deployment_swarm', 'active')


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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 5, 22, 23, 39, 49, 605145)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 5, 22, 23, 39, 49, 605002)'}),
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
            'Meta': {'object_name': 'App'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'repo_url': ('django.db.models.fields.CharField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'})
        },
        'deployment.build': {
            'Meta': {'ordering': "['-id']", 'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.App']"}),
            'end_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_time': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '20'}),
            'tag': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'deployment.configvalue': {
            'Meta': {'object_name': 'ConfigValue'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'value': ('deployment.fields.YAMLDictField', [], {})
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
            'Meta': {'object_name': 'Host'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'}),
            'squad': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'hosts'", 'null': 'True', 'to': "orm['deployment.Squad']"})
        },
        'deployment.profile': {
            'Meta': {'unique_together': "(('app', 'name'),)", 'object_name': 'Profile'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.App']"}),
            'configvalues': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['deployment.ConfigValue']", 'through': "orm['deployment.ProfileConfig']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'deployment.profileconfig': {
            'Meta': {'unique_together': "(('configvalue', 'profile'),)", 'object_name': 'ProfileConfig'},
            'configvalue': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.ConfigValue']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Profile']"}),
            'translations': ('deployment.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'})
        },
        'deployment.release': {
            'Meta': {'ordering': "['-id']", 'object_name': 'Release'},
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Build']"}),
            'config': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Profile']"})
        },
        'deployment.squad': {
            'Meta': {'object_name': 'Squad'},
            'balancer': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'deployment.swarm': {
            'Meta': {'object_name': 'Swarm'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'pool': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'proc_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Profile']"}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Release']"}),
            'size': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'squad': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Squad']"})
        }
    }

    complete_apps = ['deployment']
