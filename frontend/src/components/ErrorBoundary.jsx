import React from "react";

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    // You can log error info here if needed
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-red-900 text-red-100 p-6 rounded-xl mt-8 max-w-xl mx-auto">
          <h2 className="text-2xl font-bold mb-2">Something went wrong.</h2>
          <pre className="whitespace-pre-wrap">{this.state.error?.toString()}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;