import clsx from 'clsx'

export function Card({ className = '', children, ...props }) {
  return (
    <div className={clsx('ui-card', className)} {...props}>
      {children}
    </div>
  )
}

export function CardHeader({ className = '', children, ...props }) {
  return (
    <div className={clsx('ui-card-header', className)} {...props}>
      {children}
    </div>
  )
}

export function CardTitle({ className = '', children, ...props }) {
  return (
    <h2 className={clsx('ui-card-title', className)} {...props}>
      {children}
    </h2>
  )
}

export function CardDescription({ className = '', children, ...props }) {
  return (
    <p className={clsx('ui-card-description', className)} {...props}>
      {children}
    </p>
  )
}

export function CardContent({ className = '', children, ...props }) {
  return (
    <div className={clsx('ui-card-content', className)} {...props}>
      {children}
    </div>
  )
}
