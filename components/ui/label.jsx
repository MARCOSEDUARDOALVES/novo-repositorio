import clsx from 'clsx'

export function Label({ className = '', children, ...props }) {
  return (
    <label className={clsx('ui-label', className)} {...props}>
      {children}
    </label>
  )
}
