from .models import VisitorSession


class VisitorTrackingMiddleware:
    """
    Creates/updates VisitorSession for every request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key

        visitor, created = VisitorSession.objects.get_or_create(
            session_id=session_key
        )

        if request.user.is_authenticated:
            if visitor.user != request.user:
                visitor.user = request.user
                visitor.save(update_fields=["user", "last_seen"])

        request.visitor = visitor

        return self.get_response(request)