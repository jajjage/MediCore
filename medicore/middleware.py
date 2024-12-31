# middleware.py
class DebugTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(f"Incoming request host: {request.get_host()}")
        print(f"Request META SERVER_NAME: {request.META.get('SERVER_NAME')}")
        print(f"Request META HTTP_HOST: {request.META.get('HTTP_HOST')}")

        response = self.get_response(request)
        return response
