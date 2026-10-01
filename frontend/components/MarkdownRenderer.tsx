"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

function isSafeUrl(url?: string): boolean {
  if (!url) return false;
  const trimmed = url.trim().toLowerCase();
  return (
    trimmed.startsWith("http://") ||
    trimmed.startsWith("https://") ||
    trimmed.startsWith("mailto:")
  );
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = React.memo(
  function MarkdownRenderer({ content, className = "" }) {
    if (!content) return null;

    return (
      <div className={`markdown-content text-xs leading-relaxed ${className}`}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({ children }) => (
              <h1 className="text-sm font-bold text-slate-100 mt-2.5 mb-1 pb-0.5 border-b border-slate-800">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-xs font-bold text-slate-100 mt-2 mb-1">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-xs font-semibold text-slate-200 mt-1.5 mb-0.5">
                {children}
              </h3>
            ),
            p: ({ children }) => (
              <p className="mb-2 last:mb-0 leading-relaxed text-slate-200">
                {children}
              </p>
            ),
            strong: ({ children }) => (
              <strong className="font-semibold text-white">
                {children}
              </strong>
            ),
            em: ({ children }) => (
              <em className="italic text-slate-200">
                {children}
              </em>
            ),
            ul: ({ children }) => (
              <ul className="list-disc list-outside pl-4 space-y-1 mb-2 text-slate-200">
                {children}
              </ul>
            ),
            ol: ({ children }) => (
              <ol className="list-decimal list-outside pl-4 space-y-1 mb-2 text-slate-200">
                {children}
              </ol>
            ),
            li: ({ children }) => (
              <li className="leading-relaxed">
                {children}
              </li>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-2 border-cyan-500/60 pl-3 my-2 text-slate-400 italic bg-cyan-950/20 py-1 rounded-r">
                {children}
              </blockquote>
            ),
            table: ({ children }) => (
              <div className="overflow-x-auto my-3 rounded-xl border border-slate-800">
                <table className="min-w-full divide-y divide-slate-800 text-left text-xs">
                  {children}
                </table>
              </div>
            ),
            thead: ({ children }) => (
              <thead className="bg-slate-900/80 text-cyan-300 font-semibold">{children}</thead>
            ),
            tbody: ({ children }) => (
              <tbody className="divide-y divide-slate-800/60 bg-slate-950/40 text-slate-200">{children}</tbody>
            ),
            tr: ({ children }) => (
              <tr className="hover:bg-slate-900/40 transition-colors">{children}</tr>
            ),
            th: ({ children }) => (
              <th className="px-3 py-2 text-[11px] font-bold uppercase tracking-wider">{children}</th>
            ),
            td: ({ children }) => (
              <td className="px-3 py-2 text-xs leading-normal">{children}</td>
            ),
            a: ({ href, children }) => {
              const safe = isSafeUrl(href);
              return (
                <a
                  href={safe ? href : "#"}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2 transition-colors font-medium"
                >
                  {children}
                </a>
              );
            },
            code: ({ className, children, ...props }) => {
              const isBlock = Boolean(className);
              if (isBlock) {
                return (
                  <code className={`${className} font-mono text-[11px]`} {...props}>
                    {children}
                  </code>
                );
              }
              return (
                <code
                  className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 font-mono text-[11px] border border-slate-700/60"
                  {...props}
                >
                  {children}
                </code>
              );
            },
            pre: ({ children }) => (
              <pre className="my-2 p-3 rounded-xl bg-slate-950/90 border border-slate-800 overflow-x-auto text-slate-200 font-mono text-[11px] leading-relaxed">
                {children}
              </pre>
            ),
            hr: () => <hr className="border-slate-800 my-2.5" />,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  }
);
