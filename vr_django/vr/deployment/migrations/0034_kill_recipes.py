# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Swarm', fields ['squad', 'recipe', 'proc_name']
        db.delete_unique('deployment_swarm', ['squad_id', 'recipe_id', 'proc_name'])

        db.rename_column('deployment_release', 'env_vars', 'env_yaml')
        db.rename_column('deployment_release', 'config', 'config_yaml')

        # Adding field 'Swarm.name'
        db.add_column('deployment_swarm', 'name',
                      self.gf('django.db.models.fields.CharField')(default='anonymous', max_length=50),
                      keep_default=False)

        # Adding field 'Swarm.app'
        db.add_column('deployment_swarm', 'app',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['deployment.App'], null=True),
                      keep_default=False)

        # Adding field 'Swarm.config_yaml'
        db.add_column('deployment_swarm', 'config_yaml',
                      self.gf('vr.deployment.fields.YAMLDictField')(default=''),
                      keep_default=False)

        # Adding field 'Swarm.env_yaml'
        db.add_column('deployment_swarm', 'env_yaml',
                      self.gf('vr.deployment.fields.YAMLDictField')(default=''),
                      keep_default=False)

        # Adding M2M table for field config_ingredients on 'Swarm'
        db.create_table('deployment_swarm_config_ingredients', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('swarm', models.ForeignKey(orm['deployment.swarm'], null=False)),
            ('configingredient', models.ForeignKey(orm['deployment.configingredient'], null=False))
        ))
        db.create_unique('deployment_swarm_config_ingredients', ['swarm_id', 'configingredient_id'])

        # Adding unique constraint on 'Swarm', fields ['app', 'squad', 'proc_name']
        db.create_unique('deployment_swarm', ['app_id', 'squad_id', 'proc_name'])

        db.rename_column('deployment_configingredient', 'value', 'config_yaml')
        db.add_column('deployment_configingredient', 'env_yaml',
                      self.gf('vr.deployment.fields.YAMLDictField')(default=''),
                      keep_default=False)

        db.rename_column('deployment_configingredient', 'label', 'name')

        # Deleting field 'Build.env_vars'
        db.rename_column('deployment_build', 'env_vars', 'env_yaml')


    def backwards(self, orm):
        raise RuntimeError("Cannot reverse this migration.")


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
            'config_yaml': ('vr.deployment.fields.YAMLDictField', [], {}),
            'env_yaml': ('vr.deployment.fields.YAMLDictField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        'deployment.configrecipe': {
            'Meta': {'ordering': "('app__name', 'name')", 'unique_together': "(('app', 'name'),)", 'object_name': 'ConfigRecipe'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.App']"}),
            'env_vars': ('vr.deployment.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ingredients': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['deployment.ConfigIngredient']", 'through': "orm['deployment.RecipeIngredient']", 'symmetrical': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
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
        'deployment.recipeingredient': {
            'Meta': {'ordering': "['order']", 'unique_together': "(('ingredient', 'recipe'),)", 'object_name': 'RecipeIngredient'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ingredient': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.ConfigIngredient']"}),
            'order': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'recipe': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.ConfigRecipe']"})
        },
        'deployment.release': {
            'Meta': {'ordering': "['-id']", 'object_name': 'Release'},
            'build': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.Build']"}),
            'config_yaml': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'env_yaml': ('vr.deployment.fields.YAMLDictField', [], {'null': 'True', 'blank': 'True'}),
            'hash': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recipe': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.ConfigRecipe']"})
        },
        'deployment.squad': {
            'Meta': {'ordering': "('name',)", 'object_name': 'Squad'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '50'})
        },
        'deployment.swarm': {
            'Meta': {'ordering': "['recipe__app__name', 'recipe__name', 'proc_name']", 'unique_together': "(('app', 'squad', 'proc_name'),)", 'object_name': 'Swarm'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.App']", 'null': 'True'}),
            'balancer': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'config_ingredients': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['deployment.ConfigIngredient']", 'symmetrical': 'False'}),
            'config_yaml': ('vr.deployment.fields.YAMLDictField', [], {}),
            'env_yaml': ('vr.deployment.fields.YAMLDictField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'pool': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'proc_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'recipe': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['deployment.ConfigRecipe']"}),
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
