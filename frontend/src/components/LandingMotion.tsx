import { useEffect, useRef, type CSSProperties, type ReactNode } from 'react';

/** Observe once; only mark offscreen content hidden. No observer means visible content. */
export function Reveal({children, className = '', delay = 0}: {children: ReactNode; className?: string; delay?: number}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = ref.current;
    if (!element || !('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    if (element.getBoundingClientRect().top > window.innerHeight) element.dataset.reveal = 'waiting';
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {element.dataset.reveal = 'visible'; observer.disconnect();}
    }, {threshold: 0.08});
    observer.observe(element);
    return () => {observer.disconnect(); delete element.dataset.reveal;};
  }, []);
  return <div ref={ref} className={`reveal ${className}`} style={{'--reveal-delay': `${delay}ms`} as CSSProperties}>{children}</div>;
}

export function useReadingProgress() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let frame = 0;
    const update = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        const max = document.documentElement.scrollHeight - window.innerHeight;
        ref.current?.style.setProperty('--read-progress', String(max > 0 ? window.scrollY / max : 0));
        frame = 0;
      });
    };
    update(); window.addEventListener('scroll', update, {passive: true}); window.addEventListener('resize', update);
    return () => {cancelAnimationFrame(frame); window.removeEventListener('scroll', update); window.removeEventListener('resize', update);};
  }, []);
  return ref;
}
