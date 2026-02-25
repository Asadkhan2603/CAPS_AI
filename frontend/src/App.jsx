import { AppRoutes } from './routes/AppRoutes';
import ErrorBoundary from './components/system/ErrorBoundary';

export default function App() {
  return (
    <ErrorBoundary>
      <AppRoutes />
    </ErrorBoundary>
  );
}
