from typing import Optional, Iterable

import mistune

from .utils import from_datetime, to_datetime

class WordPressPost:
    # https://developer.wordpress.org/rest-api/reference/posts/
    @classmethod
    def from_markdown(cls, metadata, markdown, *, wp_api=None):
        data = dict(metadata)
        data["date"] = from_datetime(data["date"])
        data["modified"] = from_datetime(data.get("modified", data["date"]))
        if "categories" in data:
            assert wp_api is not None
            categories = set(cat.strip() for cat in data["categories"].split(","))
            cat_ids = set()
            for (cat_id, (name, slug, desc)) in wp_api.categories.items():
                if name in categories:
                    cat_ids.add(cat_id)
                    categories.remove(name)
            for new_category in categories:
                new_cat = wp_api.post("wp/v2/categories", json={"name": new_category})
                cat_ids.add(new_cat["id"])
            data["categories"] = ",".join([str(cat_id) for cat_id in cat_ids])
        for preprocessor in data.pop("preprocess", "").split(","):
            if not preprocessor:
                continue
            if preprocessor == "leading_spaces":
                print("adding leading spaces...")
                markdown = preserve_leading_spaces(markdown)
            else:
                raise ValueError(f"Unknown preprocessor: {preprocessor!r}")
        md = mistune.Markdown()
        html = md(markdown)
        data["content"] = html
        return cls(data, wp_api=wp_api)

    def __init__(self, data, *, wp_api=None):
        self.data = data
        self.wp_api = wp_api
    
    def copy(self, wp_api=None, **with_data):
        new_data = self.data.copy()
        new_data.update(with_data)
        wp_api = self.wp_api if wp_api is None else wp_api
        return WordPressPost(new_data, wp_api=wp_api)

    def __repr__(self):
        title = self.data["title"]["rendered"]
        author = self.data["author"] # TODO -- need to match this to author name
        created = self.data["date"]
        modified = self.data["modified"]
        on = created if created == modified else f"{created} ({modified})"
        return f"<Post {title!r} by {author} on {on}>"

    def save(self):
        assert self.wp_api is not None
        existing_id = self.data.get("id")
        if existing_id is None:
            existing_post = self.wp_api.posts.get(self.data["slug"])
            if existing_post is not None:
                existing_id = existing_post.data["id"]
            else:
                print("none existing:", self.data["slug"])
        post_to_url = "wp/v2/posts/"
        if existing_id is not None:
            print("updating existing:", existing_id)
            post_to_url += str(existing_id)
        result = self.wp_api.post(post_to_url, json=self.data)
        assert result["slug"] == self.data["slug"]

class WordPressPostsProxy:
    # todo -- filtering, select by tags, setting, etc.
    def __init__(self, wp_api):
        self.wp_api = wp_api

    def __iter__(self) -> Iterable[WordPressPost]:
        for post_data in self.wp_api.paged("wp/v2/posts"):
            yield WordPressPost(post_data, wp_api=self.wp_api)

    def get(self, slug) -> Optional[WordPressPost]:
        # have to check every status :eyeroll:
        for status in ["publish", "future", "draft", "pending", "private"]:
            posts = list(self.wp_api.paged("wp/v2/posts", slug=slug, status=status))
            if posts:
                if self.wp_api.debug and len(posts) > 1:
                    print(posts)
                assert len(posts) == 1
                return WordPressPost(posts[0], wp_api=self.wp_api)
        return None

    def __getitem__(self, slug) -> WordPressPost:
        # todo -- allow key to be post_id, or date range
        if isinstance(slug, str):
            result = self.get(slug)
            if result is None:
                raise KeyError(f"Post with slug {slug} not found on WordPress at {self.wp_api.host}")
            return result

    def __setitem__(self, slug, post: WordPressPost):
        slugged_post = post.copy(slug=slug, wp_api=self.wp_api)
        slugged_post.save()


