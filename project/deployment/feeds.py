from django.contrib.syndication.views import Feed

from deployment.models import DeploymentLogEntry

class DeploymentLogFeed(Feed):
	title = "Deployment Log"
	link = "/log/"
	description = "Application deployment details"

	def items(self):
		return DeploymentLogEntry.objects

	def item_title(self, entry):
		return "activity by {entry.user} at {entry.time}".format(entry=entry)

	def item_description(self, entry):
		return unicode(entry)
