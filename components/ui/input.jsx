import { forwardRef } from 'react'
import clsx from 'clsx'

export const Input = forwardRef(function Input({ className = '', type = 'text', ...props }, ref) {
  return (
    <input
      ref={ref}
      type={type}
      className={clsx('ui-input', className)}
      {...props}
    />
  )
})
