# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'DeploymentLogEntry'
        db.create_table('deployment_deploymentlogentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('message', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('deployment', ['DeploymentLogEntry'])

        # Adding model 'ConfigValue'
        db.create_table('deployment_configvalue', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('setting_name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('value', self.gf('yamlfield.fields.YAMLField')()),
        ))
        db.send_create_signal('deployment', ['ConfigValue'])

        # Adding model 'App'
        db.create_table('deployment_app', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('repo_url', self.gf('django.db.models.fields.CharField')(max_length=200, null=True, blank=True)),
        ))
        db.send_create_signal('deployment', ['App'])

        # Adding model 'Profile'
        db.create_table('deployment_profile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=50)),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['deployment.App'])),
        ))
        db.send_create_signal('deployment', ['Profile'])

        # Adding M2M table for field configvalues on 'Profile'
        db.create_table('deployment_profile_configvalues', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('profile', models.ForeignKey(orm['deployment.profile'], null=False)),
            ('configvalue', models.ForeignKey(orm['deployment.configvalue'], null=False))
        ))
        db.create_unique('deployment_profile_configvalues', ['profile_id', 'configvalue_id'])

        # Adding model 'Build'
        db.create_table('deployment_build', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('app', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['deployment.App'])),
        ))
        db.send_create_signal('deployment', ['Build'])

        # Adding model 'Release'
        db.create_table('deployment_release', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('build', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['deployment.Build'])),
            ('config', self.gf('yamlfield.fields.YAMLField')()),
        ))
        db.send_create_signal('deployment', ['Release'])

        # Adding model 'Host'
        db.create_table('deployment_host', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=200)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal('deployment', ['Host'])


    def backwards(self, orm):
        
        # Deleting model 'DeploymentLogEntry'
        db.delete_table('deployment_deploymentlogentry')

        # Deleting model 'ConfigValue'
        db.delete_table('deployment_configvalue')

        # Deleting model 'App'
        db.delete_table('deployment_app')

        # Deleting model 'Profile'
        db.delete_table('deployment_profile')

        # Removing M2M table for field configvalues on 'Profile'
        db.delete_table('deployment_profile_configvalues')

        # Deleting model 'Build'
        db.delete_table('deployment_build')

        # Deleting model 'Release'
        db.delete_table('deployment_release')

        # Deleting model 'Host'
        db.delete_table('deployment_host')


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
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 4, 14, 12, 46, 20, 759868)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 4, 14, 12, 46, 20, 759782)'}),
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
            'setting_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'value': ('yamlfield.fields.YAMLField', [], {})
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
            'configvalues': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['deployment.ConfigValue']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        'deployment.release': {
            'Meta': {'object_name': 'Release'},
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Build']"}),
            'config': ('yamlfield.fields.YAMLField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['deployment']
