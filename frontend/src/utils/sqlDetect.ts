/** 判断文本是否像可执行的 SELECT SQL（用于决定是否展示 SQL 框） */
export function isLikelySql(text: string | null | undefined): boolean {
  if (!text?.trim()) return false;

  let s = text.trim();
  if (s.startsWith('```')) {
    const lines = s.split('\n');
    lines.shift();
    if (lines.length > 0 && lines[lines.length - 1].trim() === '```') {
      lines.pop();
    }
    s = lines.join('\n').trim();
  }

  const upper = s.toUpperCase();
  if (!upper.startsWith('SELECT') && !upper.startsWith('WITH')) {
    return false;
  }

  // 明显是 Markdown 说明文而非 SQL
  if (s.includes('###') || s.includes('|---|') || /^#{1,6}\s/m.test(s)) {
    return false;
  }
  if (/^\|.+\|/m.test(s) && s.includes('|')) {
    return false;
  }
  if (!upper.includes('FROM') && s.split('\n').length > 2) {
    return false;
  }

  return true;
}

/** 非 SQL 文本合并进 Markdown 正文 */
export function resolveAssistantContent(msg: { content?: string; sql?: string | null }): {
  markdown: string;
  sql: string | null;
} {
  const rawSql = msg.sql?.trim() || '';
  if (!rawSql) {
    return { markdown: msg.content || '', sql: null };
  }
  if (isLikelySql(rawSql)) {
    return { markdown: msg.content || '', sql: rawSql };
  }
  const parts = [msg.content?.trim(), rawSql].filter(Boolean);
  return { markdown: parts.join('\n\n'), sql: null };
}
