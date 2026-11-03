import { createPostAction } from "@/app/actions";
import { PostForm } from "@/components/post-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CATEGORIES } from "@/lib/posts";

export default function NewPostPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">글쓰기</CardTitle>
      </CardHeader>
      <CardContent>
        <PostForm action={createPostAction} categories={CATEGORIES} submitLabel="등록" cancelHref="/" />
      </CardContent>
    </Card>
  );
}
