import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { addCommentAction, deleteCommentAction } from "@/app/actions";
import { DeletePostButton } from "@/components/delete-post-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { formatDateTime } from "@/lib/format";
import { getPost, incrementViews } from "@/lib/posts";

type Params = Promise<{ id: string }>;

export default function PostPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <PostDetail params={params} />
    </Suspense>
  );
}

async function PostDetail({ params }: { params: Params }) {
  const { id } = await params;
  await incrementViews(id);
  const post = await getPost(id);
  if (!post) notFound();

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="space-y-3">
          <div>
            <Badge variant={post.category === "공지" ? "default" : "secondary"}>{post.category}</Badge>
          </div>
          <CardTitle className="text-2xl leading-snug break-words">{post.title}</CardTitle>
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{post.author}</span>
            <span>{formatDateTime(post.createdAt)}</span>
            {post.updatedAt !== post.createdAt && <span>(수정됨 {formatDateTime(post.updatedAt)})</span>}
            <span>조회 {post.views}</span>
          </div>
        </CardHeader>
        <Separator />
        <CardContent className="min-h-40 py-6 whitespace-pre-wrap break-words leading-relaxed">
          {post.content}
        </CardContent>
        <Separator />
        <CardFooter className="justify-between pt-6">
          <Button variant="outline" size="sm" asChild>
            <Link href="/">목록</Link>
          </Button>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" asChild>
              <Link href={`/posts/${post.id}/edit`}>수정</Link>
            </Button>
            <DeletePostButton id={post.id} />
          </div>
        </CardFooter>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">댓글 {post.comments.length}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {post.comments.length === 0 ? (
            <p className="text-sm text-muted-foreground">첫 댓글을 남겨보세요.</p>
          ) : (
            <ul className="divide-y">
              {post.comments.map((c) => (
                <li key={c.id} className="flex items-start justify-between gap-4 py-3">
                  <div className="min-w-0 space-y-1">
                    <p className="text-sm">
                      <span className="font-medium">{c.author}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{formatDateTime(c.createdAt)}</span>
                    </p>
                    <p className="whitespace-pre-wrap break-words text-sm">{c.content}</p>
                  </div>
                  <form action={deleteCommentAction.bind(null, post.id, c.id)}>
                    <Button type="submit" variant="ghost" size="sm" className="text-muted-foreground">
                      삭제
                    </Button>
                  </form>
                </li>
              ))}
            </ul>
          )}

          <Separator />

          <form action={addCommentAction.bind(null, post.id)} className="space-y-3">
            <Input name="author" placeholder="작성자" maxLength={20} required className="sm:w-48" />
            <Textarea name="content" placeholder="댓글을 입력하세요" rows={3} required />
            <div className="flex justify-end">
              <Button type="submit" size="sm">
                댓글 등록
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
