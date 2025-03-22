# Keyword Arguments

## Basic Parameters

In general, basic parameters can be passed directly as keyword
arguments.

For example, `canvasapi.course.Course.get_users` has several basic
parameters including `search_term` and `user_id`, as shown in the
[Canvas Docs for List Users in
Course](https://canvas.instructure.com/doc/api/courses.html#method.courses.users).

Given an existing `canvasapi.course.Course` object, `course`, the
parameter `search_term` can be passed like this:

``` python
course.get_users(search_term='John Doe')
```

Multiple basic arguments can be passed. In this case, `enrollment_role`
has also been added.

``` python
course.get_users(
    search_term='John Doe',
    enrollment_role='StudentEnrollment'
)
```

## List Parameters

Some endpoints have parameters that are designed to be passed a list.
These usually look like `foo[]`.

For example, `canvasapi.course.Course.get_users` has a few list
parameters: `enrollment_type[]`, `include[]`, `user_ids[]`, and
`enrollment_state[]`, as shown in the [Canvas Docs for List Users in
Course](https://canvas.instructure.com/doc/api/courses.html#method.courses.users).
To use these parameters, just pass a list to the keyword. CanvasAPI will
automatically detect the list and convert the parameter to the right
format. For instance, `enrollment_type[]` can be passed like this:

``` python
course.get_users(enrollment_type=['teacher', 'student'])
```

Multiple list parameters can be passed, including in combination with
basic parameters. For this example, `include[]` and `search_term` have
been added. Note that even though only one option was sent to
`include[]`, it is still a list.

``` python
course.get_users(
    enrollment_type=['teacher', 'student'],
    search_term='John',
    include=['email']
)
```

## Nested Parameters

Some endpoints have parameters that look like `foo[bar]`. Typically,
there will be multiple parameters with the same prefix in the same
endpoint.

For example, `canvasapi.account.Account.create_course` has several
parameters that look like `course[foo]`, as shown in the [Canvas Docs
for Create a New
Course](https://canvas.instructure.com/doc/api/courses.html#method.courses.create).
However, square brackets are not valid characters for Python variables,
so the following would **NOT** work:

``` python
# This is not valid, and will not work.
account.create_course(course[name]='Example Course')
```

What Canvas is effectively doing with the bracket format is grouping
things into objects. To achieve a similar effect in Python, CanvasAPI
uses dictionaries.

Given an existing `canvasapi.account.Account` object, `account`, the
parameter `course[name]` can be passed like this:

``` python
account.create_course(course={'name': 'Example Course'})
```

In the background, CanvasAPI will combine the keys of the dictionary
with the keyword of the argument, and ultimately send the correct
variable to Canvas.

The benefit of this pattern is that multiple parameters with the same
prefix can be sent to the same keyword argument. So to pass the
`course[name]`, `course[course_code]`, and `course[is_public]`
arguments, it would look like this:

``` python
account.create_course(
    course={
        'name': 'Example Course',
        'course_code': 'TST1234',
        'is_public': True
    }
)
```

Nested parameters work easily alongside basic (and list) parameters. For
example, `offer` and `enroll_me`:

``` python
account.create_course(
    course={
        'name': 'Example Course',
        'course_code': 'TST1234',
        'is_public': True
    },
    enroll_me=True,
    offer=False
)
```

## Complex Parameters

The three main types of parameters (basic, list, and nested) from above
cover most types of parameters Canvas expects. However, there are some
types that look deceptively more complex than they actually are. Below
are some examples of how to handle these in CanvasAPI.

### Deep Nested Parameters

`canvasapi.user.User.edit` has the parameter `user[avatar][url]`, as
shown in the [Canvas Docs for Edit a
User](https://canvas.instructure.com/doc/api/users.html#method.users.update).
Any parameter that takes the form of `foo[bar1][bar2]` with multiple
bracketed sub-parameters follows the same rules as normal nested
parameters, but with deeper nesting.

``` python
user.edit(
    user={
        'avatar': {
            'url': 'http://example.com/john_avatar.png'
        }
    }
)
```

### List of Nested Parameters

`canvasapi.account.Account.add_grading_standards` has the parameters
`grading_scheme_entry[][name]` and `grading_scheme_entry[][value]`, as
shown in the [Canvas Docs for Create a New Grading
Standard](https://canvas.instructure.com/doc/api/grading_standards.html#method.grading_standards_api.create).
Any parameter that takes the form of `foo[][bar]` can be represented by
a list of dictionaries.

``` python
account.add_grading_standards(
    title='New Grading Standard',
    grading_scheme_entry=[
        {
            'name': 'A',
            'value': 90
        },
        {
            'name': 'B',
            'value': 80
        }
    ]
)
```

### Nested List Parameters

`canvasapi.course.Course.create_assignment` has the parameters
`assignment[submission_types][]` and `assignment[allowed_extensions][]`,
as shown in the [Canvas Docs for Create an
Assignment](https://canvas.instructure.com/doc/api/assignments.html#method.assignments_api.create).
Any parameter that takes the form of `foo[bar][]` is a nested parameter
of which the value is a list.

``` python
course.create_assignment(
    assignment={
        'name': 'Assignment 1',
        'submission_types': ['online_text_entry', 'online_upload'],
        'allowed_extensions': ['doc', 'docx']
    }
)
```
