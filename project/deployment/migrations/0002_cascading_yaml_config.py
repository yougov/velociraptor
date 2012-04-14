# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'ProfileConfig'
        db.create_table('deployment_profileconfig', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('configvalue', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['deployment.ConfigValue'])),
            ('profile', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['deployment.Profile'])),
            ('order', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('translations', self.gf('deployment.models.YAMLDictField')(null=True, blank=True)),
        ))
        db.send_create_signal('deployment', ['ProfileConfig'])

        # Adding unique constraint on 'ProfileConfig', fields ['configvalue', 'profile']
        db.create_unique('deployment_profileconfig', ['configvalue_id', 'profile_id'])

        # Changing field 'Release.config'
        db.alter_column('deployment_release', 'config', self.gf('deployment.models.YAMLDictField')(null=True))

        # Removing M2M table for field configvalues on 'Profile'
        db.delete_table('deployment_profile_configvalues')

        # Deleting field 'ConfigValue.setting_name'
        db.delete_column('deployment_configvalue', 'setting_name')

        # Changing field 'ConfigValue.value'
        db.alter_column('deployment_configvalue', 'value', self.gf('deployment.models.YAMLDictField')())


    def backwards(self, orm):
        
        # Removing unique constraint on 'ProfileConfig', fields ['configvalue', 'profile']
        db.delete_unique('deployment_profileconfig', ['configvalue_id', 'profile_id'])

        # Deleting model 'ProfileConfig'
        db.delete_table('deployment_profileconfig')

        # User chose to not deal with backwards NULL issues for 'Release.config'
        raise RuntimeError("Cannot reverse this migration. 'Release.config' and its values cannot be restored.")

        # Adding M2M table for field configvalues on 'Profile'
        db.create_table('deployment_profile_configvalues', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('profile', models.ForeignKey(orm['deployment.profile'], null=False)),
            ('configvalue', models.ForeignKey(orm['deployment.configvalue'], null=False))
        ))
        db.create_unique('deployment_profile_configvalues', ['profile_id', 'configvalue_id'])

        # User chose to not deal with backwards NULL issues for 'ConfigValue.setting_name'
        raise RuntimeError("Cannot reverse this migration. 'ConfigValue.setting_name' and its values cannot be restored.")

        # Changing field 'ConfigValue.value'
        db.alter_column('deployment_configvalue', 'value', self.gf('yamlfield.fields.YAMLField')())


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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 4, 14, 12, 51, 33, 441394)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 4, 14, 12, 51, 33, 438618)'}),
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
            'Meta': {'object_name': 'Build'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.App']"}),
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'deployment.configvalue': {
            'Meta': {'object_name': 'ConfigValue'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'}),
            'value': ('deployment.models.YAMLDictField', [], {})
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
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '200'})
        },
        'deployment.profile': {
            'Meta': {'object_name': 'Profile'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.App']"}),
            'configvalues': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['deployment.ConfigValue']", 'through': "orm['deployment.ProfileConfig']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        'deployment.profileconfig': {
            'Meta': {'unique_together': "(('configvalue', 'profile'),)", 'object_name': 'ProfileConfig'},
            'configvalue': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.ConfigValue']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'profile': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Profile']"}),
            'translations': ('deployment.models.YAMLDictField', [], {'null': 'True', 'blank': 'True'})
        },
        'deployment.release': {
            'Meta': {'object_name': 'Release'},
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Build']"}),
            'config': ('deployment.models.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['deployment']
