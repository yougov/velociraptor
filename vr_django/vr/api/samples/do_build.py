"""
This script demonstrates how to interact with the API to start a build and then
watch the event stream to be notified of its progress.
"""

import json
import urllib
import urlparse

import requests
import sseclient

sess = requests.session()
sess.auth = ('vagrant', 'vagrant')

API_URL = 'http://localhost:8000/api/v1/'

# Make an app record, if vr_node_example isn't already there.
app_name = 'vr_node_example'
app_url = API_URL + 'apps/%s/' % app_name

r = sess.get(app_url)

if r.status_code == 404:
    # App not found.  Make it!
    app_data = json.dumps({
        "name": app_name,
        "repo_type": "hg",
        "repo_url": "https://bitbucket.org/btubbs/vr_node_example"
    })
    r = sess.post(API_URL + 'apps/', data=app_data)

    # Throw exception and bail out if this fails
    r.raise_for_status()

# Make a buildpack record, if necessary.  Buildpacks don't have nice natural
# keys like apps do, so we'll search.
node_buildpack_url = 'https://github.com/heroku/heroku-buildpack-nodejs.git'
buildpack_search_url = API_URL + 'buildpacks/?' + urllib.urlencode({
    'repo_url': node_buildpack_url
})
r = sess.get(buildpack_search_url)
results = r.json()['objects']
if not len(results):
    # Not buildpack record found with that URL.  Make one.
    buildpack_data = json.dumps({
        'repo_url': node_buildpack_url,
        'repo_type': 'git',
        'order': 0,
    })
    r = sess.post(API_URL + 'buildpacks/', data=buildpack_data)
    assert r.status_code == 201

# Make a build record
build_data = json.dumps({
    'app': urlparse.urlparse(app_url).path,
    'tag': 'v4',
})
r = sess.post(API_URL + 'builds/', data=build_data)
assert r.status_code == 201
build_url = r.headers['location']


# Tell VR to build it
r = sess.post(build_url + 'go/')

# Watch the output
stream_url = 'http://localhost:8000/api/streams/events/'
for message in sseclient.SSEClient(stream_url, auth=sess.auth):
    print message.id, message
    # TODO: Disconnect when it says we're done
