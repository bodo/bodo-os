You see here some Django boilerplate.
This should grow into the backend for a multi-purpose mentoring/tutoring/event/learning platform.
For now, let's focus on the management of learning paths.


## General

- Use Django best practices
- Keep code extensible and clean
- Make ready for deploy, utilizing postgres (via recommended plugins for managing that)
- use poetry (NOT `requirements.txt`). Run `poetry add` instead of hallucinating version numbers

## Features/Spec

This app has two main interactions modes:

- via django admin, managing everything
- via Django REST framework, talking to the learner-side frontend (implemented in pure vue as a SPA)

The admin (=superuser) should be able to add/edit/administrate learning paths.

LearningPaths can be public or private.
Add an endpoint for all public learning paths.

They can also be assigned to users (many2many).

Use a `UserProfile` model with one2one to Django's user model to manage per-user data.

A `LearningPath` has a title, and may have a description.
It then has steps (`LearningPathStep`), as many as needed (one2many).

A step is simply a container arbitrary with a list with an arbitrary mount of `LearningPathStepBlock`s.

Each block may either be an image (with an optional caption) or simply text (as in textarea).

Then, there must be some stuff to map user(profiles) to learning paths, via a `LearningPathProgress` object.
We neeed to persist on the server which of the path's steps are unstarted, started and finished.
Also, per path, which the last step is that the user has worked on.
Think about a smart data model for this.

### Local-First

As a special feature, the learner-side frontend should have local-first/offline capabilities via rxDB.
For that, we may need to offer some special endpoints to support that.
I brainstormed a little in [this file](RX_DB_INSPIRATION.md), but I'm not sure if that's the smartest approach.
Think of a lean, clean way of syncing the user's progress objects with the postgres db without building our own sync engine.

### Auth

We need some simple auth and registration in the frontend, meaning the REST stuff has to support this.
Use `djangorestframework-simplejwt`, keep it simple.
Do the basic stuff for now, ignore fancy passwort reset flows and all that, this is a prototype only.

Implemnt useful authenticated routes, such as getting learning path progress for a learning path for a user, getting assigned learning paths for authenticated user, getting started learning paths for authenticated user.