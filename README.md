# Editing Bay

Machine Cinema review gallery. Implementation is developed in review branches.

## Git-linked Vercel project

The `editingbay` Vercel project deploys this repository on each push. The gallery needs verified media files that stay out of Git, so these deploys cannot build it. The root `vercel.json` serves the holding page in `public/` in place of a 404. Publish the real gallery from a verified `dist/` build, as the review-branch README describes.
