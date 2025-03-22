# Exceptions

CanvasAPI may return a number of different exceptions, which are listed
below.

## Quick Guide

|  |  |  |
|----|----|----|
| **Exception** | **Status Code** | **Explanation** |
| `~canvasapi.exceptions.BadRequest` | 400 | Canvas was unable to process the request. |
| `~canvasapi.exceptions.InvalidAccessToken` | 401 | The supplied API key is invalid. |
| `~canvasapi.exceptions.Unauthorized` | 401 | CanvasAPI's key is valid, but is unauthorized to access the requested resource. |
| `~canvasapi.exceptions.Forbidden` | 403 | Canvas has denied access to the resource for this user. |
| `~canvasapi.exceptions.RateLimitExceeded` | 403 | Canvas is throttling this request. Try again later. |
| `~canvasapi.exceptions.ResourceDoesNotExist` | 404 | Canvas could not locate the requested resource. |
| `~canvasapi.exceptions.Conflict` | 409 | Canvas had a conflict with an existing resource. |
| `~canvasapi.exceptions.UnprocessableEntity` | 422 | Canvas was unable to process the request. |
| `~canvasapi.exceptions.RequiredFieldMissing` | N/A | A required keyword argument was not included. |
| `~canvasapi.exceptions.CanvasException` | N/A | An unknown error was thrown. |

## Class Reference

<div class="autoclass" members="">

canvasapi.exceptions.CanvasException

The `~canvasapi.exceptions.CanvasException` exception is a basic library
exception that all other exceptions inherit from. It is also thrown
whenever an error occurs but a more specific exception isn't available
or appropriate.

Here's a simple example of catching a
`~canvasapi.exceptions.CanvasException`:

``` python
from canvasapi.exceptions import CanvasException

try:
    canvas.get_course(1)
except CanvasException as e:
    print(e)
```

</div>

<div class="autoclass" members="">

canvasapi.exceptions.BadRequest

The `~canvasapi.exceptions.BadRequest` exception is thrown when Canvas
returns an HTTP 400 error.

</div>

<div class="autoclass" members="">

canvasapi.exceptions.InvalidAccessToken

The `~canvasapi.exceptions.InvalidAccessToken` exception is thrown when
Canvas returns an HTTP 401 error and includes a `WWW-Authenticate`
header.

This indicates that the supplied API Key is invalid.

</div>

<div class="autoclass" members="">

canvasapi.exceptions.Unauthorized

The `~canvasapi.exceptions.Unauthorized` exception is thrown when Canvas
returns an HTTP 401 error and does **NOT** include a `WWW-Authenticate`
header.

This indicates that the supplied API Key is probably valid, but the
calling user does not have permission to access this resource.

</div>

<div class="autoclass" members="">

canvasapi.exceptions.ResourceDoesNotExist

The `~canvasapi.exceptions.ResourceDoesNotExist` exception is thrown
when Canvas returns an HTTP 404 error.

</div>

<div class="autoclass" members="">

canvasapi.exceptions.RequiredFieldMissing

The `~canvasapi.exceptions.RequiredFieldMissing` exception is thrown
when required fields are not passed to a method's keyword arguments.
This is common in cases where the required field must be represented as
a dictionary. See our [documentation on keyword
arguments](keyword-args.html) for examples of how to use keyword
arguments in CanvasAPI.

</div>

<div class="autoclass" members="">

canvasapi.exceptions.Forbidden

The `~canvasapi.exceptions.Forbidden` exception is thrown when Canvas
returns an HTTP 403 error.

</div>

<div class="autoclass" members="">

canvasapi.exceptions.RateLimitExceeded

The `~canvasapi.exceptions.RateLimitExceeded` exception is thrown when
Canvas returns an HTTP 403 error that includes the body "403 Forbidden
(Rate Limit Exceeded)". It will include the value of the
`X-Rate-Limit-Remaining` header (if available) for reference.

</div>

<div class="autoclass" members="">

canvasapi.exceptions.Conflict

The `~canvasapi.exceptions.Conflict` exception is thrown when Canvas
returns an HTTP 409 error.

</div>

<div class="autoclass" members="">

canvasapi.exceptions.UnprocessableEntity

The `~canvasapi.exceptions.UnprocessableEntity` exception is thrown when
Canvas returns an HTTP 422 error.

</div>
