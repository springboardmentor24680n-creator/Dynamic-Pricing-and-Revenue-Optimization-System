import { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useForm } from 'react-hook-form';
import GoogleSignInButton from '../components/auth/GoogleSignInButton';
import {
  Sparkles, Eye, EyeOff, Loader2, CheckCircle2, RotateCcw,
} from 'lucide-react';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [rejectedMessage, setRejectedMessage] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm();

  useEffect(() => {
    if (location.state?.message) {
      setSuccessMsg(location.state.message);
      window.history.replaceState({}, document.title);
    }
  }, [location.state?.message]);

  const onSubmit = async (data) => {
    setError('');
    setSuccessMsg('');
    setRejectedMessage('');
    setLoading(true);
    try {
      const result = await login(data);
      // Account verified but awaiting administrator approval - no session issued.
      if (result?.access_pending) {
        sessionStorage.setItem('pending_email', result.email || '');
        sessionStorage.setItem('pending_name', result.name || '');
        navigate('/access-pending', {
          state: { email: result.email, name: result.name, provider: result.provider },
        });
        return;
      }
      navigate('/dashboard');
    } catch (err) {
      if (err.response?.status === 401) {
        setError('Invalid username or password. Please try again.');
      } else if (err.response?.status === 403) {
        setError(err.response?.data?.detail || 'Your account has been deactivated. Contact your administrator.');
        // Rejected access requests can be re-submitted from the sign-up page
        if (String(err.response?.data?.detail || '').toLowerCase().includes('rejected')) {
          setError('');
          setRejectedMessage(err.response?.data?.detail || 'Your access request was rejected by the administrator.');
        }
      } else {
        setError(err.response?.data?.detail || 'Sign in failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-surface-50 via-primary-50/30 to-surface-50 dark:from-surface-950 dark:via-primary-950/20 dark:to-surface-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md animate-fade-in">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 shadow-lg shadow-primary-500/25 mb-4">
            <Sparkles className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-surface-900 dark:text-white">
            Welcome back
          </h1>
          <p className="text-surface-500 dark:text-surface-400 mt-1">
            Sign in to your PricePilot AI account
          </p>
        </div>

        {/* Login form */}
        <div className="bg-white dark:bg-surface-800 rounded-2xl shadow-xl border border-surface-200 dark:border-surface-700 p-8">
          {/* Success message */}
          {successMsg && (
            <div className="mb-5 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 text-sm text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              {successMsg}
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="mb-5 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-600 dark:text-red-400">
              {error}
            </div>
          )}

          {/* Rejected request - re-request path */}
          {rejectedMessage && (
            <div className="mb-5 p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-sm text-amber-600 dark:text-amber-400">
              <p>{rejectedMessage}</p>
              <button
                type="button"
                onClick={() => navigate('/register', { state: { reRequest: true } })}
                className="mt-2 inline-flex items-center gap-1.5 font-medium text-amber-700 dark:text-amber-300 hover:underline"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Request access again
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div>
              <label className="label">Username</label>
              <input
                type="text"
                className={`input ${errors.username ? 'input-error' : ''}`}
                placeholder="Enter your username"
                {...register('username', { required: 'Username is required' })}
              />
              {errors.username && (
                <p className="error-text">{errors.username.message}</p>
              )}
            </div>

            <div>
              <label className="label">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  className={`input pr-10 ${errors.password ? 'input-error' : ''}`}
                  placeholder="Enter your password"
                  {...register('password', { required: 'Password is required' })}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400 hover:text-surface-600 dark:hover:text-surface-300"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="error-text">{errors.password.message}</p>
              )}
            </div>

            {/* Forgot Password Link */}
            <div className="flex justify-end -mt-3">
              <Link
                to="/forgot-password"
                className="text-xs font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 transition-colors"
              >
                Forgot password?
              </Link>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : null}
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-surface-200 dark:border-surface-700"></div>
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-white dark:bg-surface-800 px-3 text-surface-400 dark:text-surface-500">
                Or continue with
              </span>
            </div>
          </div>

          {/* Google Sign-In Button (official OAuth) */}
          <GoogleSignInButton />

          {/* Register link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-surface-500 dark:text-surface-400">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="text-primary-600 dark:text-primary-400 hover:text-primary-700 font-medium"
              >
                Create one
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
