# Troubleshooting

If you're just starting out with CanvasAPI, you may run into exceptions
right out of the gate. Below are a few common issues to check for.

## URL Formatting

Confirm that the Canvas URL you're passing into the `canvasapi.Canvas`
object as `base_url` is properly formatted:

- Starts with `https://` (Only use `http` if absolutely neccessary)
- Does **NOT** include `/api/v1/`
- Does **NOT** have a trailing slash
- Does **NOT** have leading or trailing whitespace

### Bad URL Examples (Avoid These!)

- `"example.edu"`
- `"http://example.edu"`
- `"https://example.edu/api/v1/"`
- `"https://example.edu/"`
- `"https://canvas.example.edu/"`
- `"https://example.edu/canvas/"`
- `" https://example.edu"`
- `"https://example.edu "`

### Good URL Examples

- `"https://example.edu"`
- `"https://canvas.example.edu"`
- `"https://example.edu/canvas"`

## Access Token

CanvasAPI expects an access token, **NOT** a developer key. If you have
a developer key, you'll need to follow the [OAuth2
process](https://canvas.instructure.com/doc/api/file.oauth.html) to get
the access token for a user.

To create an access token as your user without a developer key, you can
create one manually through the Canvas LMS user interface. Go to Account
\> Settings, then scroll down to the "Approved Integrations" section and
click the "New Access Token" button.

You can test your new access token manually with a third-party tool like
[curl](https://curl.se/docs/manpage.html) or
[Postman](https://www.postman.com/). To test with CanvasAPI, call
`canvasapi.Canvas.get_current_user` and check if returns the appropriate
user information.

Ensure the token you provide to CanvasAPI is correctly formatted:

- Does **NOT** have leading or trailing whitespace
- Does **NOT** contain `Bearer` (CanvasAPI will add this for you, where
  appropriate)
- Includes the shard ID, separated by `~` (if applicable)
- Is a valid (non-expired) token
- Is the full length token (usually 64 characters, not including the
  shard ID)

### Bad Access Token Examples (Avoid these!)

- `" 7H155up3r53CR3770K3n15n07R34L4Nd5h0uLDN0783u53dpL34534nd7H4nKY0u"`
- `"7H155up3r53CR3770K3n15n07R34L4Nd5h0uLDN0783u53dpL34534nd7H4nKY0u "`
- `"Bearer 7H155up3r53CR3770K3n15n07R34L4Nd5h0uLDN0783u53dpL34534nd7H4nKY0u"`
- `"1 7H155up3r53CR3770K3n15n07R34L4Nd5h0uLDN0783u53dpL34534nd7H4nKY0u"`
- `"7H155up3r53CR3770K3n15n07R34L4Nd5h0uLDN0783u53dpL34534nd7H4nKY0"`

### Good Access Token Examples

- `"7H155up3r53CR3770K3n15n07R34L4Nd5h0uLDN0783u53dpL34534nd7H4nKY0u"`
- `"1~7H155up3r53CR3770K3n15n07R34L4Nd5h0uLDN0783u53dpL34534nd7H4nKY0u"`

## User Permissions

You may recieve unexpected `~canvasapi.exceptions.Unauthorized` or
`~canvasapi.exceptions.Forbidden` exceptions. It is also possible to get
`~canvasapi.exceptions.ResourceDoesNotExist` exceptions for objects that
actually do exist. These are usually signs of the user lacking
sufficient permissions to access the endpoint.

To determine if the issue is related to a bad access token or
insufficent permissions, use the test described in [Access
Token](#access-token) above. If that works properly but you still can't
access the other endpoints, your user may not have the permissions
required to use that endpoint. You may need to discuss your permission
levels with your Canvas LMS Administrator.

## Still Have a Problem?

If you've checked for and corrected these common mistakes but are still
encountering an unexpected issue, please look at our [instructions for
setting up logging in CanvasAPI](debugging.html). This may help find the
issue.

If you need further assistance, please [create an issue on
GitHub](https://github.com/ucfopen/canvasapi/issues/new/choose) or join
us in the `#canvasapi` channel on the [UCF Open Source
Slack](https://ucf-open-slackin.herokuapp.com/). There are lots of
friendly folks willing to help you figure out what's going on!
