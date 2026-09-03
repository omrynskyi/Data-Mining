'use client';

import { useEffect, useId, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Check, ChevronDown } from 'lucide-react';

interface DropdownProps {
  label: string;
  options: readonly string[];
  value: string;
  onChange: (val: string) => void;
  renderOption?: (option: string) => React.ReactNode;
}

/**
 * Listbox-pattern select. The previous version was a div with a click handler:
 * no roles, no keyboard access, no focus management.
 */
export default function CustomDropdown({
  label,
  options,
  value,
  onChange,
  renderOption,
}: DropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(() => Math.max(0, options.indexOf(value)));
  const wrapRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const listId = useId();
  const labelId = useId();

  useEffect(() => {
    if (!isOpen) return;
    const onPointerDown = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setIsOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [isOpen]);

  // Focus moves into the list once it exists; the highlighted index is set by
  // whichever handler opened the menu, not by an effect.
  useEffect(() => {
    if (isOpen) listRef.current?.focus();
  }, [isOpen]);

  const open = () => {
    setActiveIndex(Math.max(0, options.indexOf(value)));
    setIsOpen(true);
  };

  const commit = (option: string) => {
    onChange(option);
    setIsOpen(false);
    triggerRef.current?.focus();
  };

  const onListKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveIndex((i) => (i + 1) % options.length);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveIndex((i) => (i - 1 + options.length) % options.length);
        break;
      case 'Home':
        e.preventDefault();
        setActiveIndex(0);
        break;
      case 'End':
        e.preventDefault();
        setActiveIndex(options.length - 1);
        break;
      case 'Enter':
      case ' ':
        e.preventDefault();
        commit(options[activeIndex]);
        break;
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        triggerRef.current?.focus();
        break;
    }
  };

  return (
    <div className="field" ref={wrapRef} style={{ position: 'relative' }}>
      <span className="field-label" id={labelId}>
        {label}
      </span>
      <button
        ref={triggerRef}
        type="button"
        className="select-trigger"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-labelledby={`${labelId} ${listId}-value`}
        onClick={() => (isOpen ? setIsOpen(false) : open())}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown' || e.key === 'Enter') {
            e.preventDefault();
            open();
          }
        }}
      >
        <span id={`${listId}-value`}>{renderOption ? renderOption(value) : value}</span>
        <motion.span
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.15 }}
          style={{ display: 'inline-flex', color: 'var(--text-3)' }}
        >
          <ChevronDown size={15} strokeWidth={1.75} />
        </motion.span>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            ref={listRef}
            role="listbox"
            tabIndex={-1}
            aria-labelledby={labelId}
            aria-activedescendant={`${listId}-opt-${activeIndex}`}
            className="popover"
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.13, ease: [0.16, 1, 0.3, 1] }}
            onKeyDown={onListKeyDown}
            style={{ outline: 'none' }}
          >
            {options.map((option, index) => {
              const selected = option === value;
              return (
                <button
                  key={option}
                  id={`${listId}-opt-${index}`}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  data-active={index === activeIndex}
                  className="option"
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => commit(option)}
                >
                  <span style={{ flex: 1 }}>{renderOption ? renderOption(option) : option}</span>
                  {selected && <Check size={14} strokeWidth={2} />}
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
