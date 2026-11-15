import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';

interface TooltipProps {
  anchor: DOMRect | null;
  id: string;
  children: ReactNode;
}

const MARGIN = 8;

// Tooltip flutuante: acima da célula, ou abaixo quando não cabe. Nunca sai da tela.
export function Tooltip({ anchor, id, children }: TooltipProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!anchor || !el) return;
    const { width, height } = el.getBoundingClientRect();
    const vw = window.innerWidth;
    let left = anchor.left + anchor.width / 2 - width / 2;
    left = Math.max(MARGIN, Math.min(vw - width - MARGIN, left));
    let top = anchor.top - height - MARGIN;
    if (top < MARGIN) top = anchor.bottom + MARGIN;
    setPos({ left, top });
  }, [anchor, children]);

  if (!anchor) return null;
  return (
    <div
      ref={ref}
      id={id}
      role="tooltip"
      className="tip"
      style={{ left: pos?.left ?? -9999, top: pos?.top ?? -9999 }}
    >
      {children}
    </div>
  );
}
