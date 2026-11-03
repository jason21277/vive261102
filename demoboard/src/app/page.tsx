import Link from "next/link";
import { unstable_rethrow } from "next/navigation";
import { Suspense } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDate } from "@/lib/format";
import { CATEGORIES, describeDbError, listPosts } from "@/lib/posts";
import { cn } from "@/lib/utils";

type SearchParams = Promise<{ q?: string; category?: string; page?: string }>;

export default function HomePage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <CardTitle className="text-xl">게시판</CardTitle>
        <Button asChild>
          <Link href="/posts/new">글쓰기</Link>
        </Button>
      </CardHeader>
      <CardContent>
        <Suspense fallback={<BoardSkeleton />}>
          <Board searchParams={searchParams} />
        </Suspense>
      </CardContent>
    </Card>
  );
}

function buildHref(params: { q?: string; category?: string; page?: number }) {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.category) sp.set("category", params.category);
  if (params.page && params.page > 1) sp.set("page", String(params.page));
  const qs = sp.toString();
  return qs ? `/?${qs}` : "/";
}

async function Board({ searchParams }: { searchParams: SearchParams }) {
  const { q = "", category = "", page } = await searchParams;
  let result: Awaited<ReturnType<typeof listPosts>>;
  try {
    result = await listPosts({ q, category, page: Number(page) || 1 });
  } catch (err) {
    unstable_rethrow(err); // let Next.js handle its own control-flow errors (e.g. prerender aborts)
    console.error(err);
    return (
      <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm">
        <p className="font-medium text-destructive">데이터베이스에 연결하지 못했습니다.</p>
        <p className="mt-1 break-words text-muted-foreground">{describeDbError(err)}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap gap-2">
          {["", ...CATEGORIES].map((c) => (
            <Button
              key={c || "all"}
              asChild
              size="sm"
              variant={category === c ? "default" : "outline"}
            >
              <Link href={buildHref({ q, category: c })}>{c || "전체"}</Link>
            </Button>
          ))}
        </div>
        <form action="/" className="flex gap-2">
          {category && <input type="hidden" name="category" value={category} />}
          <Input name="q" defaultValue={q} placeholder="제목, 내용, 작성자 검색" className="md:w-64" />
          <Button type="submit" variant="secondary">
            검색
          </Button>
        </form>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="hidden w-16 text-center sm:table-cell">번호</TableHead>
            <TableHead className="w-20 text-center">분류</TableHead>
            <TableHead>제목</TableHead>
            <TableHead className="hidden w-28 md:table-cell">작성자</TableHead>
            <TableHead className="hidden w-24 text-center md:table-cell">작성일</TableHead>
            <TableHead className="hidden w-16 text-center sm:table-cell">조회</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {result.items.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                게시글이 없습니다.
              </TableCell>
            </TableRow>
          ) : (
            result.items.map((post, i) => (
              <TableRow key={post.id}>
                <TableCell className="hidden text-center text-muted-foreground sm:table-cell">
                  {result.total - (result.page - 1) * result.pageSize - i}
                </TableCell>
                <TableCell className="text-center">
                  <Badge variant={post.category === "공지" ? "default" : "secondary"}>{post.category}</Badge>
                </TableCell>
                <TableCell className="max-w-0 w-full">
                  <Link href={`/posts/${post.id}`} className="flex items-center gap-1.5 hover:underline">
                    <span className="truncate font-medium">{post.title}</span>
                    {post.commentCount > 0 && (
                      <span className="shrink-0 text-xs text-primary">[{post.commentCount}]</span>
                    )}
                  </Link>
                  <p className="text-xs text-muted-foreground md:hidden">
                    {post.author} · {formatDate(post.createdAt)}
                  </p>
                </TableCell>
                <TableCell className="hidden md:table-cell">{post.author}</TableCell>
                <TableCell className="hidden text-center text-muted-foreground md:table-cell">
                  {formatDate(post.createdAt)}
                </TableCell>
                <TableCell className="hidden text-center text-muted-foreground sm:table-cell">{post.views}</TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {result.totalPages > 1 && (
        <nav className="flex justify-center gap-1" aria-label="페이지">
          {Array.from({ length: result.totalPages }, (_, i) => i + 1).map((n) => (
            <Button
              key={n}
              asChild
              size="sm"
              variant={n === result.page ? "default" : "ghost"}
              className={cn("w-9")}
            >
              <Link href={buildHref({ q, category, page: n })}>{n}</Link>
            </Button>
          ))}
        </nav>
      )}

      <p className="text-right text-xs text-muted-foreground">총 {result.total}개의 글</p>
    </div>
  );
}

function BoardSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-9 w-full" />
      {Array.from({ length: 5 }, (_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}
