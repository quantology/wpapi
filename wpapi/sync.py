from pathlib import Path

import frontmatter

from .posts import WordPressPost

def sync_markdown_directory(dir_path, wp_api):
    for p in Path(dir_path).iterdir():
        if p.suffix.lower() == ".md":
            post = frontmatter.load(p.open())
            metadata = dict(post.metadata)
            metadata.setdefault("slug", p.stem)
            metadata.setdefault("status", "publish")
            wp_post = WordPressPost.from_markdown(metadata, post.content, wp_api=wp_api)
            wp_post.save()
