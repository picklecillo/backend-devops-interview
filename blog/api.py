from django.shortcuts import get_object_or_404
from ninja import Router

from blog.models import Post, Tag, User
from blog.schemas import (
    CommentCreateIn,
    CommentCreateOut,
    PostCreateIn,
    PostCreateOut,
    PostDetailOut,
    PostListOut,
    UserDetailOut,
)
from blog.services import CommentService, PostService

router = Router()


def _serialize_author(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
    }


def _serialize_tag(tag: Tag) -> dict:
    return {"id": tag.id, "name": tag.name, "slug": tag.slug}


def _serialize_post_list(post: Post) -> dict:
    return {
        "id": post.id,
        "title": post.title,
        "author": _serialize_author(post.author),
        "tags": [_serialize_tag(t) for t in post.tags.all()],
        "view_count": post.view_count,
        "created_at": post.created_at,
    }


POSTS_PAGE_SIZE = 100


@router.get("/posts", response=list[PostListOut])
def list_posts(request, page: int = 1):
    start = (page - 1) * POSTS_PAGE_SIZE
    posts = PostService.list_posts()[start : start + POSTS_PAGE_SIZE]
    return [_serialize_post_list(p) for p in posts]


@router.get("/posts/search", response=list[PostListOut])
def search_posts(request, q: str, page: int = 1):
    start = (page - 1) * POSTS_PAGE_SIZE
    posts = PostService.search_posts(q)[start : start + POSTS_PAGE_SIZE]
    return [_serialize_post_list(p) for p in posts]


@router.get("/posts/by-tag/{slug}", response=list[PostListOut])
def posts_by_tag(request, slug: str, page: int = 1):
    start = (page - 1) * POSTS_PAGE_SIZE
    posts = PostService.posts_by_tag(slug)[start : start + POSTS_PAGE_SIZE]
    return [_serialize_post_list(p) for p in posts]


@router.get("/posts/{post_id}", response=PostDetailOut)
def get_post(request, post_id: int):
    post = PostService.get_post(post_id)

    comments = [
        {
            "id": c.id,
            "author": _serialize_author(c.author),
            "body": c.body,
            "created_at": c.created_at,
        }
        for c in CommentService.comments_for_post(post)
    ]
    return {
        "id": post.id,
        "title": post.title,
        "body": post.body,
        "author": _serialize_author(post.author),
        "tags": [_serialize_tag(t) for t in post.tags.all()],
        "comments": comments,
        "view_count": post.view_count,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
    }


@router.post("/posts", response=PostCreateOut)
def create_post(request, payload: PostCreateIn):
    post = PostService.create_post(
        author_id=payload.author_id,
        title=payload.title,
        body=payload.body,
        tag_slugs=payload.tag_slugs,
    )
    return {"id": post.id, "title": post.title}


@router.post("/posts/{post_id}/comments", response=CommentCreateOut)
def create_comment(request, post_id: int, payload: CommentCreateIn):
    comment = CommentService.create_comment(
        post_id=post_id, author_id=payload.author_id, body=payload.body
    )
    return {"id": comment.id}


@router.get("/users/find", response=UserDetailOut)
def find_user_by_email(request, email: str):
    user = get_object_or_404(User, email=email)
    return _user_detail(user)


@router.get("/users/{user_id}", response=UserDetailOut)
def get_user(request, user_id: int):
    user = get_object_or_404(User, id=user_id)
    return _user_detail(user)


def _user_detail(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "email": user.email,
        "bio": user.bio,
        "post_count": user.posts.count(),
        "comment_count": user.comments.count(),
    }
