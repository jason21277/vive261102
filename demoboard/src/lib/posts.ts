import "server-only";

import { neon } from "@neondatabase/serverless";

export const CATEGORIES = ["공지", "자유", "질문", "정보"] as const;
export type Category = (typeof CATEGORIES)[number];

export type Comment = {
  id: string;
  author: string;
  content: string;
  createdAt: string;
};

export type Post = {
  id: string;
  title: string;
  content: string;
  author: string;
  category: Category;
  views: number;
  createdAt: string;
  updatedAt: string;
  comments: Comment[];
};

export type PostSummary = Omit<Post, "content" | "comments"> & { commentCount: number };

export type PostInput = Pick<Post, "title" | "content" | "author" | "category">;

if (!process.env.DATABASE_URL) {
  throw new Error("DATABASE_URL is not set. Add it to .env.local.");
}
const sql = neon(process.env.DATABASE_URL);

type Row = Record<string, unknown>;
const iso = (v: unknown) => (v instanceof Date ? v : new Date(String(v))).toISOString();

function toSummary(r: Row): PostSummary {
  return {
    id: r.id as string,
    title: r.title as string,
    author: r.author as string,
    category: r.category as Category,
    views: Number(r.views),
    createdAt: iso(r.created_at),
    updatedAt: iso(r.updated_at),
    commentCount: Number(r.comment_count ?? 0),
  };
}

function toComment(r: Row): Comment {
  return {
    id: r.id as string,
    author: r.author as string,
    content: r.content as string,
    createdAt: iso(r.created_at),
  };
}

// Creates the tables (and sample posts) the first time this process touches the DB.
let ready: Promise<void> | undefined;
function ensureSchema() {
  ready ??= (async () => {
    await sql`
      CREATE TABLE IF NOT EXISTS posts (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        title text NOT NULL,
        content text NOT NULL,
        author text NOT NULL,
        category text NOT NULL,
        views integer NOT NULL DEFAULT 0,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now()
      )`;
    await sql`
      CREATE TABLE IF NOT EXISTS comments (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        post_id uuid NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        author text NOT NULL,
        content text NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now()
      )`;
    await sql`CREATE INDEX IF NOT EXISTS comments_post_id_idx ON comments(post_id)`;

    const [{ count }] = await sql`SELECT count(*)::int AS count FROM posts`;
    if (count > 0) return;
    const [welcome] = await sql`
      INSERT INTO posts (title, content, author, category, views, created_at, updated_at)
      VALUES (
        'DemoBoard에 오신 것을 환영합니다',
        E'Next.js, shadcn/ui, TypeScript로 만든 데모 게시판입니다.\n\n글쓰기, 수정, 삭제, 댓글, 검색, 카테고리 필터를 지원합니다.',
        '관리자', '공지', 42, now() - interval '48 hours', now() - interval '48 hours'
      )
      RETURNING id`;
    await sql`
      INSERT INTO comments (post_id, author, content, created_at)
      VALUES (${welcome.id}, '방문자', '깔끔하네요!', now() - interval '40 hours')`;
    await sql`
      INSERT INTO posts (title, content, author, category, views, created_at, updated_at) VALUES
        ('Server Actions 사용 팁 공유합니다',
         '폼 제출을 API 라우트 없이 서버 함수로 바로 처리할 수 있어서 편합니다.',
         '개발자', '정보', 17, now() - interval '20 hours', now() - interval '20 hours'),
        ('shadcn 컴포넌트 커스터마이징은 어떻게 하나요?',
         'components/ui 아래 파일을 직접 수정하면 되는 건가요?',
         '초보', '질문', 8, now() - interval '5 hours', now() - interval '5 hours')`;
  })().catch((err) => {
    ready = undefined;
    throw err;
  });
  return ready;
}

export type ListOptions = {
  q?: string;
  category?: string;
  page?: number;
  pageSize?: number;
};

export async function listPosts({ q, category, page = 1, pageSize = 10 }: ListOptions) {
  await ensureSchema();
  const cat = category && (CATEGORIES as readonly string[]).includes(category) ? category : null;
  const pattern = q ? `%${q.replace(/[\\%_]/g, (m) => `\\${m}`)}%` : null;

  const [{ total }] = await sql`
    SELECT count(*)::int AS total FROM posts
    WHERE (${cat}::text IS NULL OR category = ${cat})
      AND (${pattern}::text IS NULL OR title ILIKE ${pattern} OR content ILIKE ${pattern} OR author ILIKE ${pattern})`;

  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const current = Math.min(Math.max(1, page), totalPages);

  const rows = await sql`
    SELECT p.id, p.title, p.author, p.category, p.views, p.created_at, p.updated_at,
           (SELECT count(*) FROM comments c WHERE c.post_id = p.id) AS comment_count
    FROM posts p
    WHERE (${cat}::text IS NULL OR p.category = ${cat})
      AND (${pattern}::text IS NULL OR p.title ILIKE ${pattern} OR p.content ILIKE ${pattern} OR p.author ILIKE ${pattern})
    ORDER BY p.created_at DESC
    LIMIT ${pageSize} OFFSET ${(current - 1) * pageSize}`;

  return { items: rows.map(toSummary), total: total as number, page: current, totalPages, pageSize };
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function getPost(id: string): Promise<Post | null> {
  if (!UUID_RE.test(id)) return null;
  await ensureSchema();
  const [row] = await sql`SELECT * FROM posts WHERE id = ${id}`;
  if (!row) return null;
  const comments = await sql`SELECT * FROM comments WHERE post_id = ${id} ORDER BY created_at`;
  const { commentCount: _, ...summary } = toSummary(row);
  return { ...summary, content: row.content as string, comments: comments.map(toComment) };
}

export async function incrementViews(id: string) {
  if (!UUID_RE.test(id)) return;
  await ensureSchema();
  await sql`UPDATE posts SET views = views + 1 WHERE id = ${id}`;
}

export async function createPost(input: PostInput) {
  await ensureSchema();
  const [row] = await sql`
    INSERT INTO posts (title, content, author, category)
    VALUES (${input.title}, ${input.content}, ${input.author}, ${input.category})
    RETURNING id`;
  return { id: row.id as string };
}

export async function updatePost(id: string, input: PostInput) {
  if (!UUID_RE.test(id)) return null;
  await ensureSchema();
  const [row] = await sql`
    UPDATE posts
    SET title = ${input.title}, content = ${input.content}, author = ${input.author},
        category = ${input.category}, updated_at = now()
    WHERE id = ${id}
    RETURNING id`;
  return row ? { id: row.id as string } : null;
}

export async function deletePost(id: string) {
  if (!UUID_RE.test(id)) return;
  await ensureSchema();
  await sql`DELETE FROM posts WHERE id = ${id}`;
}

export async function addComment(postId: string, author: string, content: string) {
  if (!UUID_RE.test(postId)) return;
  await ensureSchema();
  await sql`
    INSERT INTO comments (post_id, author, content)
    SELECT id, ${author}, ${content} FROM posts WHERE id = ${postId}`;
}

export async function deleteComment(postId: string, commentId: string) {
  if (!UUID_RE.test(postId) || !UUID_RE.test(commentId)) return;
  await ensureSchema();
  await sql`DELETE FROM comments WHERE id = ${commentId} AND post_id = ${postId}`;
}
