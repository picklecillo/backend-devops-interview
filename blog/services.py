from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404

from blog.models import Comment, Post, Tag, User


class PostService:
    @staticmethod
    def list_posts() -> QuerySet[Post]:
        return (
            Post.objects.filter(is_published=True)
            .select_related("author")
            .prefetch_related("tags")
            .order_by("-created_at")
        )

    @staticmethod
    def search_posts(query: str) -> QuerySet[Post]:
        return (
            Post.objects.filter(
                Q(title__icontains=query) | Q(body__icontains=query),
                is_published=True,
            )
            .select_related("author")
            .prefetch_related("tags")
            .order_by("-created_at")
        )

    @staticmethod
    def posts_by_tag(slug: str) -> QuerySet[Post]:
        tag = get_object_or_404(Tag, slug=slug)
        return (
            tag.posts.filter(is_published=True)
            .select_related("author")
            .prefetch_related("tags")
            .order_by("-created_at")
        )

    @staticmethod
    def get_post(post_id: int) -> Post:
        post = get_object_or_404(
            Post.objects.select_related("author").prefetch_related("tags"), id=post_id
        )
        post.view_count += 1
        post.save()
        return post

    @staticmethod
    def create_post(author_id: int, title: str, body: str, tag_slugs: list[str]) -> Post:
        author = get_object_or_404(User, id=author_id)
        post = Post.objects.create(author=author, title=title, body=body)
        for slug in tag_slugs:
            tag = Tag.objects.get(slug=slug)
            post.tags.add(tag)
        return post


class CommentService:
    @staticmethod
    def comments_for_post(post: Post) -> QuerySet[Comment]:
        return post.comments.select_related("author").order_by("created_at")

    @staticmethod
    def create_comment(post_id: int, author_id: int, body: str) -> Comment:
        post = get_object_or_404(Post, id=post_id)
        author = get_object_or_404(User, id=author_id)
        return Comment.objects.create(post=post, author=author, body=body)
