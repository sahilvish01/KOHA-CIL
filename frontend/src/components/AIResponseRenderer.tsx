import ReactMarkdown from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';

type AIResponseRendererProps = {
  content: string;
};

/**
 * Safely renders Markdown returned by the assistant. Raw HTML is deliberately
 * not enabled, so model output is treated as untrusted content.
 */
export default function AIResponseRenderer({ content }: AIResponseRendererProps) {
  return (
    <div className="text-[14px] leading-[1.65] text-[#3a4541]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          h1: ({ children }) => <h1 className="mb-[12px] mt-[20px] text-[22px] font-[800] leading-tight text-[#27312b] first:mt-0">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-[10px] mt-[18px] text-[19px] font-[750] leading-tight text-[#27312b] first:mt-0">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-[8px] mt-[16px] text-[16px] font-[700] leading-tight text-[#27312b] first:mt-0">{children}</h3>,
          h4: ({ children }) => <h4 className="mb-[8px] mt-[14px] text-[14px] font-[700] text-[#27312b] first:mt-0">{children}</h4>,
          p: ({ children }) => <p className="mb-[12px] last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="mb-[12px] list-disc space-y-[4px] pl-[22px] last:mb-0">{children}</ul>,
          ol: ({ children }) => <ol className="mb-[12px] list-decimal space-y-[4px] pl-[22px] last:mb-0">{children}</ol>,
          li: ({ children }) => <li className="pl-[2px]">{children}</li>,
          blockquote: ({ children }) => <blockquote className="my-[14px] border-l-[3px] border-[#b79d5f] bg-[#f7f4eb] px-[14px] py-[10px] text-[#4d584f] [&>p]:mb-0">{children}</blockquote>,
          hr: () => <hr className="my-[18px] border-0 border-t border-[#d9d8d1]" />,
          a: ({ children, href }) => <a className="text-[#2d4a3e] underline underline-offset-2" href={href}>{children}</a>,
          pre: ({ children }) => <pre className="my-[14px] overflow-x-auto rounded-[6px] border border-[#d8d6ce] bg-[#f3f2ee] p-[14px] text-[12px] leading-[1.6] text-[#26332e]">{children}</pre>,
          code: ({ children, className }) => className
            ? <code className={className}>{children}</code>
            : <code className="rounded-[3px] bg-[#ecebe6] px-[4px] py-[1px] font-mono text-[.9em] text-[#4a3922]">{children}</code>,
          table: ({ children }) => <div className="my-[14px] overflow-x-auto rounded-[6px] border border-[#dddcd6]"><table className="w-full min-w-[520px] border-collapse text-[13px]">{children}</table></div>,
          thead: ({ children }) => <thead className="bg-[#f1f0eb]">{children}</thead>,
          th: ({ children, align }) => <th className={`border-b border-[#d9d8d1] px-[14px] py-[10px] text-[12px] font-[700] text-[#4d574f] ${align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'}`}>{children}</th>,
          td: ({ children, align }) => <td className={`border-b border-[#e5e3dc] px-[14px] py-[10px] align-top ${align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'}`}>{children}</td>,
          tr: ({ children }) => <tr className="last:[&>td]:border-b-0 hover:bg-[#fafaf8]">{children}</tr>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}