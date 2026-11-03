import { notFound } from "next/navigation";
import { Suspense } from "react";

import { updatePostAction } from "@/app/actions";
import { PostForm } from "@/components/post-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CATEGORIES, getPost } from "@/lib/posts";

type Params = Promise<{ id: string }>;

export default function EditPostPage({ params }: { params: Params }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">글 수정</CardTitle>
      </CardHeader>
      <CardContent>
        <Suspense fallback={<Skeleton className="h-96 w-full" />}>
          <EditForm params={params} />
        </Suspense>
      </CardContent>
    </Card>
  );
}

async function EditForm({ params }: { params: Params }) {
  const { id } = await params;
  const post = await getPost(id);
  if (!post) notFound();

  return (
    <PostForm
      action={updatePostAction.bind(null, id)}
      categories={CATEGORIES}
      initial={{ title: post.title, content: post.content, author: post.author, category: post.category }}
      submitLabel="수정 완료"
      cancelHref={`/posts/${id}`}
    />
  );
}
