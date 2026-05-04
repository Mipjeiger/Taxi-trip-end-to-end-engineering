import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'small' | 'medium' | 'large';
  loading?: boolean;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'medium',
  loading = false,
  children,
  disabled,
  ...props
}) => {
  const styles = getButtonStyles(variant, size);
  
  return (
    <button
      style={styles}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? '⏳ Loading...' : children}
    </button>
  );
};

const getButtonStyles = (
  variant: 'primary' | 'secondary' | 'danger',
  size: 'small' | 'medium' | 'large'
): React.CSSProperties => {
  const baseStyles: React.CSSProperties = {
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    fontWeight: 'bold',
    transition: 'all 0.3s ease',
    fontSize: size === 'small' ? '0.9em' : size === 'large' ? '1.2em' : '1em',
    padding: size === 'small' ? '8px 16px' : size === 'large' ? '16px 32px' : '12px 24px',
  };

  const variantStyles: { [key: string]: React.CSSProperties } = {
    primary: {
      background: '#667eea',
      color: '#fff',
    },
    secondary: {
      background: 'transparent',
      color: '#667eea',
      border: '2px solid #667eea',
    },
    danger: {
      background: '#f56565',
      color: '#fff',
    },
  };

  return { ...baseStyles, ...variantStyles[variant] };
};