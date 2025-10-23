import { forwardRef } from 'react'
import clsx from 'clsx'

export const Button = forwardRef(function Button({ className = '', type = 'button', disabled = false, children, ...props }, ref) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled}
      className={clsx('ui-button', disabled && 'ui-button--disabled', className)}
      {...props}
    >
      {children}
    </button>
  )
})
