"use client";

import Link from "next/link";
import { useActionState } from "react";

import type { FormState } from "@/app/actions";
import type { PostInput } from "@/lib/posts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

type Props = {
  action: (state: FormState, formData: FormData) => Promise<FormState>;
  categories: readonly string[];
  initial?: PostInput;
  submitLabel: string;
  cancelHref: string;
};

export function PostForm({ action, categories, initial, submitLabel, cancelHref }: Props) {
  const [state, formAction, pending] = useActionState(action, { values: initial });
  const values = state.values ?? {};
  const errors = state.errors ?? {};

  return (
    <form action={formAction} className="space-y-5">
      {errors.form && <p className="text-sm text-destructive">{errors.form}</p>}

      <div className="grid gap-5 sm:grid-cols-[180px_1fr]">
        <div className="space-y-2">
          <Label htmlFor="category">카테고리</Label>
          <Select name="category" defaultValue={values.category ?? categories[1]}>
            <SelectTrigger id="category" className="w-full">
              <SelectValue placeholder="선택" />
            </SelectTrigger>
            <SelectContent>
              {categories.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {errors.category && <p className="text-sm text-destructive">{errors.category}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="author">작성자</Label>
          <Input id="author" name="author" defaultValue={values.author} maxLength={20} placeholder="이름" />
          {errors.author && <p className="text-sm text-destructive">{errors.author}</p>}
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="title">제목</Label>
        <Input id="title" name="title" defaultValue={values.title} maxLength={100} placeholder="제목을 입력하세요" />
        {errors.title && <p className="text-sm text-destructive">{errors.title}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="content">내용</Label>
        <Textarea
          id="content"
          name="content"
          defaultValue={values.content}
          rows={12}
          placeholder="내용을 입력하세요"
        />
        {errors.content && <p className="text-sm text-destructive">{errors.content}</p>}
      </div>

      <div className="flex justify-end gap-2">
        <Button variant="outline" asChild>
          <Link href={cancelHref}>취소</Link>
        </Button>
        <Button type="submit" disabled={pending}>
          {pending ? "저장 중..." : submitLabel}
        </Button>
      </div>
    </form>
  );
}
