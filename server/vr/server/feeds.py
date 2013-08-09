from django.contrib.syndication.views import Feed

from vr.server.models import DeploymentLogEntry

class DeploymentLogFeed(Feed):
	title = "Deployment Log"
	link = "/log"
	description = "Application deployment details"

	def items(self):
		return DeploymentLogEntry.objects.all()

	def item_link(self, entry):
		return "/log"

	def item_title(self, entry):
		return "activity by {entry.user} at {entry.time}".format(entry=entry)

	def item_description(self, entry):
		return unicode(entry)
