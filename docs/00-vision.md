# Vision

This is a project to help organize, save, and retrieve references. A reference is anything that we might find useful to come back later to. An article, an image, a collection of images, videos for a particular thing like game, and so forth. 

Examples:
- A Github repo, another a website, another a tweet. Basically each item like that gets an entry.
- We should also allow for compound entries. If the reference is for a particular game, inside might be screenshots and videos. We should be also able to organize further within this (like if some screenshots are gameplay, others UX, etc)

The store be in a regular filesystem so it can backed up on OneDrive or a NAS or even just a drive on my PC. It should also allow for connecting GitHub repos. All stores should seamlessly work together (at most we could sort/filter by stores).

References are captured by users through the app (by adding links, etc) or by agents filling it out. If its added by a user with just a link (or just a name, etc) then we can configure something to auto populate some information.

## Goals

- It should facilate the retrieval of references when needed especially for AI agents.
- Can mark some as either higher priority, favorites or ratings (maybe even negative) for retrieval and sorting reasons (exact thing TBD)
- Items can have tags and notes added to them
- There is an app where we can view, add, and manage references.
- It should provide a set of CRUD operations.
- It should support adding embeddings to facilitate search
- The store should be able to be accessed by multiple agents running on the machine, which might include updates, additions, etc.
- It should be able to be made available on the local network (not by default) so that a phone could add references.

## Non-goals

- It does not find the references (through web search or otherwise)
- Networking (except making it available on the local network at a user's own risk) and hosting.

## Principles

- It is a library first and foremost, with a CLI that is a thin wrapper. Agents learn how to use it first through the agent skill, and then exploring the CLI's --help.
- Windows support is first class.
