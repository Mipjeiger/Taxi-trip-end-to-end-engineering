import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  icon,
  className,
  ...props
}) => {
  return (
    <div className="input-wrapper">
      {label && <label>{label}</label>}
      <div className="input-group">
        {icon && <span className="input-icon">{icon}</span>}
        <input className={`input ${error ? 'error' : ''} ${className}`} {...props} />
      </div>
      {error && <span className="error-message">{error}</span>}
    </div>
  );
};