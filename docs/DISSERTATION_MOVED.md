# The dissertation chapters have moved

They now live in the writing workspace, not in the code repository:

    Thesis/thesis_writing/chapters/

Renumbered to thesis order on the way (`10-introduction.md` became
`01-introduction.md`, and so on) so the filenames match the chapter numbers
an examiner will see.

**Why they moved.** Chapters are prose destined for Overleaf; the code
repository is the research record. Keeping them here made the repo the
authority on two different things. `docs/notes/` and `docs/formulation.md`
stay, because they are the empirical and theoretical record the chapters cite
rather than the prose itself.

Their history up to `2bd14cd` remains in this repo's log:

    git log --follow -- docs/dissertation/40-results.md
