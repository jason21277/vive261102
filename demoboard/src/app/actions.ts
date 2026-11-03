"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import * as store from "@/lib/posts";
import { CATEGORIES, type Category, type PostInput } from "@/lib/posts";

export type FormState = {
  errors?: Partial<Record<keyof PostInput | "form", string>>;
  values?: Partial<PostInput>;
};

function parsePost(formData: FormData): { input?: PostInput; state?: FormState } {
  const values = {
    title: String(formData.get("title") ?? "").trim(),
    content: String(formData.get("content") ?? "").trim(),
    author: String(formData.get("author") ?? "").trim(),
    category: String(formData.get("category") ?? "") as Category,
  };
  const errors: FormState["errors"] = {};
  if (!values.title) errors.title = "제목을 입력하세요.";
  else if (values.title.length > 100) errors.title = "제목은 100자 이하로 입력하세요.";
  if (!values.content) errors.content = "내용을 입력하세요.";
  if (!values.author) errors.author = "작성자를 입력하세요.";
  if (!CATEGORIES.includes(values.category)) errors.category = "카테고리를 선택하세요.";

  if (Object.keys(errors).length) return { state: { errors, values } };
  return { input: values };
}

export async function createPostAction(_: FormState, formData: FormData): Promise<FormState> {
  const { input, state } = parsePost(formData);
  if (!input) return state!;
  const post = await store.createPost(input);
  revalidatePath("/");
  redirect(`/posts/${post.id}`);
}

export async function updatePostAction(id: string, _: FormState, formData: FormData): Promise<FormState> {
  const { input, state } = parsePost(formData);
  if (!input) return state!;
  const post = await store.updatePost(id, input);
  if (!post) return { errors: { form: "게시글을 찾을 수 없습니다." }, values: input };
  revalidatePath("/");
  revalidatePath(`/posts/${id}`);
  redirect(`/posts/${id}`);
}

export async function deletePostAction(id: string) {
  await store.deletePost(id);
  revalidatePath("/");
  redirect("/");
}

export async function addCommentAction(postId: string, formData: FormData) {
  const author = String(formData.get("author") ?? "").trim();
  const content = String(formData.get("content") ?? "").trim();
  if (!author || !content) return;
  await store.addComment(postId, author, content);
  revalidatePath(`/posts/${postId}`);
}

export async function deleteCommentAction(postId: string, commentId: string) {
  await store.deleteComment(postId, commentId);
  revalidatePath(`/posts/${postId}`);
}
