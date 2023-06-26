from cookie_request_header import CookieRequestHeader


def remove_necessary_interceptor(request, domain, logging=False):
    """
    Interceptor that removes all necessary cookies from a GET request.

    `request` is the GET request.
    """
    if request.headers.get("Cookie") is None:
        return

    cookie_header = CookieRequestHeader(domain, request.headers["Cookie"])
    cookie_header.remove_necessary()
    modified_header = cookie_header.get_header()

    if logging:
        if modified_header != request.headers["Cookie"]:
            data_path = f"./data/{domain}/"

            with open(data_path + "logs.txt", "a") as file:
                file.write(f"Original header: {request.headers['Cookie']}\n")
                file.write(f"Modified header: {modified_header}\n\n")

    request.headers["Cookie"] = modified_header


def remove_all_interceptor(request):
    """
    Interceptor that removes all cookies from a GET request.

    `request` is the GET request.
    """
    if request.headers.get("Cookie") is None:
        return

    del request.headers["Cookie"]


def passthrough_interceptor(request):
    """
    Do nothing to the GET request.
    """
    pass
