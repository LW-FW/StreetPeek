import { Html, Head, Main, NextScript } from 'next/document';
export default function Document() {
  return (
    <Html lang="en">
      <Head>
        <meta charSet="utf-8" />
        <link rel="icon" href="/favicon.ico" />
        <meta name="description" content="See what's coming to your street — planning applications, crime trends, flood risk and new developments before you buy." />
      </Head>
      <body><Main /><NextScript /></body>
    </Html>
  );
}