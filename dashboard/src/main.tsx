// 파일 경로: src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';

type EBState = { hasError: boolean; error?: string; stack?: string };

class ErrorBoundary extends React.Component<React.PropsWithChildren, EBState> {
  state: EBState = { hasError: false };

  static getDerivedStateFromError(err: unknown): EBState {
    const e = err as any;
    return {
      hasError: true,
      error: String(e?.message ?? e ?? '알 수 없는 오류'),
      stack: String(e?.stack ?? ''),
    };
  }

  componentDidCatch(err: unknown) {
    // 콘솔에도 남겨서 디버깅 가능하게
    // (여기서 외부 전송은 하지 않음)
    console.error('[Dashboard] Uncaught render error:', err);
  }

  render() {
    if (!this.state.hasError) return this.props.children;
    return (
      <div style={{
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        color: '#E7EEF9',
        fontFamily: 'Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
      }}>
        <div style={{
          width: 'min(980px, 100%)',
          background: 'rgba(10, 14, 22, 0.82)',
          border: '1px solid rgba(251, 113, 133, 0.35)',
          borderRadius: 16,
          padding: 18,
          boxShadow: '0 18px 60px rgba(0,0,0,0.45)',
        }}>
          <div style={{ fontSize: 13, fontWeight: 800, marginBottom: 8 }}>대시보드 런타임 오류</div>
          <div style={{ fontSize: 12, opacity: 0.85, marginBottom: 12 }}>
            화면이 비어 보이면 앱이 크래시 난 상태입니다. 아래 메시지를 복사해서 보내주면 즉시 원인 고칩니다.
          </div>
          <pre style={{
            margin: 0,
            fontSize: 11,
            lineHeight: 1.4,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            fontFamily: 'JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            background: 'rgba(2, 6, 23, 0.60)',
            border: '1px solid rgba(148, 163, 184, 0.18)',
            borderRadius: 14,
            padding: 12,
          }}>
{this.state.error}
{this.state.stack ? `\n\n${this.state.stack}` : ''}
          </pre>
        </div>
      </div>
    );
  }
}

// 런타임 예외가 나도 "검은 화면"이 아니라 에러 UI로 보여주기
const rootEl = document.getElementById('root');
if (!rootEl) throw new Error('#root 엘리먼트를 찾을 수 없습니다.');

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);