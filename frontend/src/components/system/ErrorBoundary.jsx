import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, message: '' };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, message: error?.message || 'Unexpected application error' };
  }

  componentDidCatch(error, info) {
    // Keep this minimal and console-based for now; can be wired to Sentry later.
    // eslint-disable-next-line no-console
    console.error('UI crash captured by ErrorBoundary', error, info);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <main className="grid min-h-screen place-items-center bg-slate-100 p-4 dark:bg-slate-950">
          <section className="w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 dark:border-slate-800 dark:bg-slate-900">
            <h1 className="text-xl font-semibold text-slate-900 dark:text-white">Something went wrong</h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{this.state.message}</p>
            <button className="btn-primary mt-4" type="button" onClick={this.handleReload}>
              Reload app
            </button>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
