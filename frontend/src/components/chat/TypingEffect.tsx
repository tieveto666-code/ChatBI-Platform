import React, { useState, useEffect, useRef } from 'react';

interface TypingEffectProps {
  text: string;
  speed?: number;
  onComplete?: () => void;
}

const TypingEffect: React.FC<TypingEffectProps> = ({ text, speed = 20, onComplete }) => {
  const [displayedText, setDisplayedText] = useState('');
  const indexRef = useRef(0);

  useEffect(() => {
    indexRef.current = 0;
    setDisplayedText('');
  }, [text]);

  useEffect(() => {
    if (indexRef.current >= text.length) {
      onComplete?.();
      return;
    }

    const timer = setTimeout(() => {
      const charsPerTick = 3;
      const nextIndex = Math.min(indexRef.current + charsPerTick, text.length);
      setDisplayedText(text.slice(0, nextIndex));
      indexRef.current = nextIndex;
    }, speed);

    return () => clearTimeout(timer);
  }, [displayedText, text, speed, onComplete]);

  return <span>{displayedText}</span>;
};

export default TypingEffect;
