import { cn } from '../../utils/cn';

export default function Card({ className, children }) {
  return <section className={cn('panel', className)}>{children}</section>;
}
