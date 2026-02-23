export default function FormInput({ label, as = 'input', className = '', ...props }) {
  const Component = as;
  return (
    <label className="block space-y-1">
      {label ? <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">{label}</span> : null}
      <Component className={`input ${className}`} {...props} />
    </label>
  );
}
