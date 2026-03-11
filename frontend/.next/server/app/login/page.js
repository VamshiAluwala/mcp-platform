(()=>{var a={};a.id=520,a.ids=[520],a.modules={261:a=>{"use strict";a.exports=require("next/dist/shared/lib/router/utils/app-paths")},846:a=>{"use strict";a.exports=require("next/dist/compiled/next-server/app-page.runtime.prod.js")},1025:a=>{"use strict";a.exports=require("next/dist/server/app-render/dynamic-access-async-storage.external.js")},1038:()=>{},1068:(a,b,c)=>{"use strict";c.r(b),c.d(b,{default:()=>k,dynamic:()=>i});var d=c(8743),e=c(8301),f=c(2378),g=c(1967),h=c(7012);let i="force-dynamic";function j(){(0,f.useRouter)();let a=(0,f.useSearchParams)(),[b,c]=(0,e.useState)(""),[i,j]=(0,e.useState)(""),[k,l]=(0,e.useState)("dark");(0,e.useRef)(!1),a.get("provider");let m=a.get("next")||"/";async function n(a){try{j(""),c(a);let b="google_direct"===a?`${window.location.origin}/auth/google/callback`:`${window.location.origin}/auth/callback`,d=(0,g.jK)(a,m),e=await fetch(`http://localhost:8000/api/auth/login-url?provider=${a}&redirect_uri=${encodeURIComponent(b)}&state=${encodeURIComponent(d)}`),f=await e.json();if(!e.ok)throw Error(f.detail||`Login failed (${e.status})`);window.location.href=f.login_url}catch(a){j(a.message),c(!1)}}let o=""!==b;return(0,d.jsxs)(d.Fragment,{children:[(0,d.jsx)("style",{children:`
        .login-root {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 32px 24px;
          background:
            radial-gradient(circle at 15% 20%, rgba(0,209,255,0.16), transparent 30%),
            radial-gradient(circle at 85% 12%, rgba(255,138,61,0.18), transparent 26%),
            linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0)),
            var(--bg);
          font-family: var(--sans);
          position: relative;
          overflow: hidden;
        }

        .login-root::before {
          content: '';
          position: absolute;
          inset: 24px;
          border: 1px solid var(--border);
          border-radius: 32px;
          pointer-events: none;
          opacity: 0.4;
        }

        .login-stage {
          width: 100%;
          max-width: 1120px;
          display: grid;
          grid-template-columns: 1.1fr 0.9fr;
          gap: 28px;
          position: relative;
          z-index: 1;
        }

        .login-brand,
        .login-card {
          position: relative;
          overflow: hidden;
          border-radius: 28px;
          border: 1px solid var(--border);
          background: linear-gradient(180deg, var(--surface), rgba(255,255,255,0.02));
          backdrop-filter: blur(18px);
          box-shadow: var(--shadow-soft);
        }

        .login-brand {
          padding: 42px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          min-height: 620px;
        }

        .login-brand::after,
        .login-card::after {
          content: '';
          position: absolute;
          inset: auto auto -80px -40px;
          width: 220px;
          height: 220px;
          background: radial-gradient(circle, rgba(255,138,61,0.22), transparent 70%);
          filter: blur(18px);
          pointer-events: none;
        }

        .login-card {
          padding: 42px 38px;
        }

        .login-badge,
        .login-card-badge {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: rgba(255,255,255,0.08);
          border: 1px solid var(--border);
          border-radius: 100px;
          padding: 6px 12px;
          font-size: 10px;
          font-weight: 600;
          color: var(--text2);
          letter-spacing: 0.06em;
          text-transform: uppercase;
          width: fit-content;
        }

        .login-card-badge {
          margin-bottom: 18px;
        }

        .login-brand-title {
          font-size: clamp(42px, 6vw, 70px);
          line-height: 0.95;
          letter-spacing: -0.06em;
          margin: 22px 0 18px;
          color: var(--text);
          max-width: 620px;
        }

        .login-brand-title span {
          color: var(--accent);
          display: block;
        }

        .login-brand-copy {
          max-width: 560px;
          font-size: 16px;
          color: var(--text2);
          line-height: 1.8;
        }

        .login-signal-row {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 14px;
          margin-top: 30px;
        }

        .login-signal {
          padding: 16px;
          border-radius: 18px;
          background: rgba(255,255,255,0.05);
          border: 1px solid var(--border);
        }

        .login-signal-label {
          display: block;
          font-family: var(--mono);
          font-size: 10px;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--text3);
          margin-bottom: 10px;
        }

        .login-signal strong {
          display: block;
          font-size: 18px;
          color: var(--text);
          margin-bottom: 6px;
        }

        .login-signal span:last-child {
          color: var(--text2);
          font-size: 13px;
          line-height: 1.6;
        }

        .login-card-title {
          font-size: 34px;
          font-weight: 700;
          color: var(--text);
          line-height: 1.1;
          margin-bottom: 8px;
          letter-spacing: -0.04em;
        }

        .login-subtitle {
          font-size: 14px;
          color: var(--text2);
          line-height: 1.6;
          margin-bottom: 30px;
        }

        .login-divider {
          display: flex;
          align-items: center;
          gap: 12px;
          margin: 18px 0;
          color: var(--text3);
          font-size: 12px;
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .login-divider::before,
        .login-divider::after {
          content: '';
          flex: 1;
          height: 1px;
          background: var(--border);
        }

        .login-btn {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          padding: 14px 20px;
          border-radius: 12px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
          border: none;
          outline: none;
          position: relative;
          overflow: hidden;
          letter-spacing: -0.01em;
        }

        .login-btn:disabled {
          opacity: 0.55;
          cursor: not-allowed;
        }

        .login-btn-keycloak {
          background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 100%);
          color: #fff;
          box-shadow: 0 18px 38px rgba(0,0,0,0.18);
        }

        .login-btn-keycloak:not(:disabled):hover {
          transform: translateY(-1px);
          box-shadow: 0 22px 44px rgba(0,0,0,0.22);
          filter: brightness(1.04);
        }

        .login-btn-keycloak:not(:disabled):active {
          transform: translateY(0);
          box-shadow: 0 12px 26px rgba(0,0,0,0.18);
        }

        .login-btn-google {
          background: var(--surface2);
          color: var(--text);
          border: 1px solid var(--border);
        }

        .login-btn-google:not(:disabled):hover {
          background: color-mix(in srgb, var(--surface2) 90%, white);
          border-color: color-mix(in srgb, var(--accent2) 40%, var(--border));
          transform: translateY(-1px);
        }

        .login-btn-google:not(:disabled):active {
          transform: translateY(0);
        }

        .spinner {
          width: 16px;
          height: 16px;
          border: 2px solid rgba(255,255,255,0.32);
          border-top-color: #fff;
          border-radius: 50%;
          animation: spin 0.65s linear infinite;
          flex-shrink: 0;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .login-error {
          margin-top: 16px;
          padding: 12px 14px;
          background: color-mix(in srgb, var(--red) 12%, transparent);
          border: 1px solid color-mix(in srgb, var(--red) 30%, transparent);
          border-radius: 14px;
          color: var(--red);
          font-size: 13px;
          line-height: 1.5;
        }

        .login-footer {
          margin-top: 24px;
          font-size: 12px;
          color: var(--text3);
          line-height: 1.7;
        }

        .login-footer a {
          color: var(--accent);
          text-decoration: none;
        }

        .login-footer a:hover {
          text-decoration: underline;
        }

        .login-theme-control {
          position: fixed;
          top: 28px;
          right: 28px;
          z-index: 3;
        }

        @media (max-width: 980px) {
          .login-stage {
            grid-template-columns: 1fr;
          }

          .login-brand {
            min-height: auto;
          }
        }

        @media (max-width: 640px) {
          .login-root {
            padding: 18px;
          }

          .login-root::before {
            inset: 10px;
            border-radius: 24px;
          }

          .login-brand,
          .login-card {
            padding: 26px 22px;
            border-radius: 22px;
          }

          .login-signal-row {
            grid-template-columns: 1fr;
          }

          .login-theme-control {
            top: 18px;
            right: 18px;
          }
        }
      `}),(0,d.jsxs)("main",{className:"login-root",children:[(0,d.jsxs)("button",{type:"button",className:"theme-toggle login-theme-control",onClick:function(){let a=(0,h.jC)(k);(0,h.AZ)(a),l(a)},"aria-label":`Switch to ${"dark"===k?"light":"dark"} mode`,children:[(0,d.jsx)("span",{className:"theme-toggle-icon",children:"dark"===k?"☀":"☾"}),(0,d.jsx)("span",{className:"theme-toggle-label",children:"dark"===k?"Light":"Dark"})]}),(0,d.jsxs)("section",{className:"login-stage",children:[(0,d.jsxs)("aside",{className:"login-brand",children:[(0,d.jsxs)("div",{children:[(0,d.jsxs)("div",{className:"login-badge",children:[(0,d.jsx)("svg",{width:"8",height:"8",viewBox:"0 0 8 8",fill:"none",children:(0,d.jsx)("circle",{cx:"4",cy:"4",r:"4",fill:"var(--accent2)"})}),"Agentorix MCP Cloud"]}),(0,d.jsxs)("h1",{className:"login-brand-title",children:["Build. Share.",(0,d.jsx)("span",{children:"Observe every MCP session."})]}),(0,d.jsx)("p",{className:"login-brand-copy",children:"A sharper control room for GitHub-backed MCP deployments with Google SSO, per-user access, live logs, and platform-grade audit visibility."})]}),(0,d.jsxs)("div",{className:"login-signal-row",children:[(0,d.jsxs)("div",{className:"login-signal",children:[(0,d.jsx)("span",{className:"login-signal-label",children:"Identity"}),(0,d.jsx)("strong",{children:"Google + Keycloak"}),(0,d.jsx)("span",{children:"SSO-first login flow for dashboard users and MCP consumers."})]}),(0,d.jsxs)("div",{className:"login-signal",children:[(0,d.jsx)("span",{className:"login-signal-label",children:"Access"}),(0,d.jsx)("strong",{children:"Email allowlists"}),(0,d.jsx)("span",{children:"Grant specific end users access to each deployed MCP."})]}),(0,d.jsxs)("div",{className:"login-signal",children:[(0,d.jsx)("span",{className:"login-signal-label",children:"Observability"}),(0,d.jsx)("strong",{children:"Sessions + audit"}),(0,d.jsx)("span",{children:"Track which user connected, what they called, and when."})]})]})]}),(0,d.jsxs)("section",{className:"login-card",children:[(0,d.jsx)("div",{className:"login-card-badge",children:"Secure workspace sign-in"}),(0,d.jsx)("h2",{className:"login-card-title",children:"Welcome back"}),(0,d.jsx)("p",{className:"login-subtitle",children:"/"!==m?"Sign in to continue straight into your MCP endpoint.":"Access deployments, sessions, and admin controls from one workspace."}),(0,d.jsx)("button",{id:"btn-keycloak-login",className:"login-btn login-btn-keycloak",onClick:()=>n("keycloak"),disabled:o,children:"keycloak"===b?(0,d.jsxs)(d.Fragment,{children:[(0,d.jsx)("div",{className:"spinner"})," Redirecting to Keycloak…"]}):(0,d.jsxs)(d.Fragment,{children:[(0,d.jsxs)("svg",{width:"18",height:"18",viewBox:"0 0 24 24",fill:"none",xmlns:"http://www.w3.org/2000/svg",children:[(0,d.jsx)("path",{d:"M12 2L2 7l10 5 10-5-10-5z",stroke:"currentColor",strokeWidth:"2",strokeLinejoin:"round"}),(0,d.jsx)("path",{d:"M2 17l10 5 10-5",stroke:"currentColor",strokeWidth:"2",strokeLinejoin:"round"}),(0,d.jsx)("path",{d:"M2 12l10 5 10-5",stroke:"currentColor",strokeWidth:"2",strokeLinejoin:"round"})]}),"Continue with Keycloak"]})}),(0,d.jsx)("div",{className:"login-divider",children:"or"}),(0,d.jsx)("button",{id:"btn-google-login",className:"login-btn login-btn-google",onClick:()=>n("google_direct"),disabled:o,children:"google_direct"===b?(0,d.jsxs)(d.Fragment,{children:[(0,d.jsx)("div",{className:"spinner",style:{borderTopColor:"#4285f4"}})," Redirecting to Google…"]}):(0,d.jsxs)(d.Fragment,{children:[(0,d.jsx)("svg",{width:"18",height:"18",viewBox:"0 0 18 18",xmlns:"http://www.w3.org/2000/svg",children:(0,d.jsxs)("g",{fill:"none",fillRule:"evenodd",children:[(0,d.jsx)("path",{d:"M17.64 9.2045c0-.6381-.0573-1.2518-.1636-1.8409H9v3.4814h4.8436c-.2086 1.125-.8427 2.0782-1.7959 2.7164v2.2582h2.9087c1.7018-1.5668 2.6836-3.874 2.6836-6.615z",fill:"#4285F4"}),(0,d.jsx)("path",{d:"M9 18c2.43 0 4.4673-.806 5.9564-2.1818l-2.9087-2.2582c-.8059.54-1.8368.859-3.0477.859-2.344 0-4.3282-1.5836-5.036-3.7104H.9574v2.3318C2.4382 15.9832 5.4818 18 9 18z",fill:"#34A853"}),(0,d.jsx)("path",{d:"M3.964 10.71c-.18-.54-.2727-1.1168-.2727-1.71s.0927-1.17.2727-1.71V4.9582H.9573C.3477 6.1731 0 7.5477 0 9s.3477 2.8268.9573 4.0418L3.964 10.71z",fill:"#FBBC05"}),(0,d.jsx)("path",{d:"M9 3.5795c1.3214 0 2.5077.4541 3.4405 1.346l2.5813-2.5814C13.4627.8918 11.4255 0 9 0 5.4818 0 2.4382 2.0168.9573 4.9582L3.964 7.29C4.6718 5.1632 6.656 3.5795 9 3.5795z",fill:"#EA4335"})]})}),"Continue with Google"]})}),i&&(0,d.jsx)("div",{className:"login-error",role:"alert",children:i}),(0,d.jsx)("p",{className:"login-footer",children:"By signing in you agree to platform access policies. After login you will be redirected to your dashboard or the MCP endpoint you requested."})]})]})]})]})}function k(){return(0,d.jsx)(e.Suspense,{fallback:(0,d.jsx)("main",{style:{minHeight:"100vh",display:"grid",placeItems:"center",padding:24,background:"#0a0a0f"},children:(0,d.jsx)("section",{style:{width:"100%",maxWidth:440,textAlign:"center",color:"#64748b",fontFamily:"sans-serif"},children:"Loading…"})}),children:(0,d.jsx)(j,{})})}},1324:(a,b,c)=>{Promise.resolve().then(c.t.bind(c,1170,23)),Promise.resolve().then(c.t.bind(c,3597,23)),Promise.resolve().then(c.t.bind(c,6893,23)),Promise.resolve().then(c.t.bind(c,9748,23)),Promise.resolve().then(c.t.bind(c,3679,23)),Promise.resolve().then(c.t.bind(c,7184,23)),Promise.resolve().then(c.t.bind(c,9576,23)),Promise.resolve().then(c.t.bind(c,3041,23)),Promise.resolve().then(c.t.bind(c,1384,23))},1967:(a,b,c)=>{"use strict";c.d(b,{B7:()=>h,BC:()=>i,WW:()=>g,b0:()=>f,jK:()=>e});let d="mcp_access_token";function e(a,b=""){if(!a)return"";try{return window.btoa(JSON.stringify({provider:a,next:b}))}catch{return a}}function f(a){if(!a)return{provider:"keycloak",next:"/"};try{let b=JSON.parse(window.atob(a));return{provider:b?.provider||"keycloak",next:b?.next||"/"}}catch{return{provider:a,next:"/"}}}function g(a){if(!a?.access_token)return;window.localStorage.setItem("mcp_access_token",a.access_token),a.refresh_token&&window.localStorage.setItem("mcp_refresh_token",a.refresh_token),a.user&&window.localStorage.setItem("mcp_user",JSON.stringify(a.user));let b=Number(a.expires_in||3600);document.cookie=`${d}=${encodeURIComponent(a.access_token)}; path=/; max-age=${b}; samesite=lax`}function h(){window.localStorage.removeItem("mcp_access_token"),window.localStorage.removeItem("mcp_refresh_token"),window.localStorage.removeItem("mcp_user"),document.cookie=`${d}=; path=/; max-age=0; samesite=lax`}function i(a,b){let c=a||"/";if(/^https?:\/\//i.test(c)){window.location.href=c;return}b.replace(c)}},2378:(a,b,c)=>{"use strict";var d=c(1330);c.o(d,"useRouter")&&c.d(b,{useRouter:function(){return d.useRouter}}),c.o(d,"useSearchParams")&&c.d(b,{useSearchParams:function(){return d.useSearchParams}})},2704:()=>{},3033:a=>{"use strict";a.exports=require("next/dist/server/app-render/work-unit-async-storage.external.js")},3295:a=>{"use strict";a.exports=require("next/dist/server/app-render/after-task-async-storage.external.js")},3873:a=>{"use strict";a.exports=require("path")},5290:(a,b,c)=>{"use strict";c.r(b),c.d(b,{default:()=>f,dynamic:()=>e});var d=c(7954);let e=(0,d.registerClientReference)(function(){throw Error("Attempted to call dynamic() from the server but dynamic is on the client. It's not possible to invoke a client function from the server, it can only be rendered as a Component or passed to props of a Client Component.")},"/app/app/login/page.js","dynamic"),f=(0,d.registerClientReference)(function(){throw Error("Attempted to call the default export of \"/app/app/login/page.js\" from the server, but it's on the client. It's not possible to invoke a client function from the server, it can only be rendered as a Component or passed to props of a Client Component.")},"/app/app/login/page.js","default")},5449:(a,b,c)=>{Promise.resolve().then(c.bind(c,1068))},6439:a=>{"use strict";a.exports=require("next/dist/shared/lib/no-fallback-error.external")},6713:a=>{"use strict";a.exports=require("next/dist/shared/lib/router/utils/is-bot")},6773:(a,b,c)=>{"use strict";c.r(b),c.d(b,{GlobalError:()=>D.a,__next_app__:()=>J,handler:()=>L,pages:()=>I,routeModule:()=>K,tree:()=>H});var d=c(9754),e=c(9117),f=c(6595),g=c(2324),h=c(6945),i=c(8928),j=c(175),k=c(7631),l=c(4290),m=c(2696),n=c(2802),o=c(7533),p=c(5229),q=c(2822),r=c(261),s=c(6453),t=c(2474),u=c(6713),v=c(1356),w=c(2685),x=c(6225),y=c(3446),z=c(2762),A=c(5742),B=c(6439),C=c(1170),D=c.n(C),E=c(2506),F=c(1203),G={};for(let a in E)0>["default","tree","pages","GlobalError","__next_app__","routeModule","handler"].indexOf(a)&&(G[a]=()=>E[a]);c.d(b,G);let H={children:["",{children:["login",{children:["__PAGE__",{},{page:[()=>Promise.resolve().then(c.bind(c,5290)),"/app/app/login/page.js"]}]},{}]},{layout:[()=>Promise.resolve().then(c.bind(c,7697)),"/app/app/layout.js"],"global-error":[()=>Promise.resolve().then(c.t.bind(c,1170,23)),"next/dist/client/components/builtin/global-error.js"],"not-found":[()=>Promise.resolve().then(c.t.bind(c,7028,23)),"next/dist/client/components/builtin/not-found.js"],forbidden:[()=>Promise.resolve().then(c.t.bind(c,461,23)),"next/dist/client/components/builtin/forbidden.js"],unauthorized:[()=>Promise.resolve().then(c.t.bind(c,2768,23)),"next/dist/client/components/builtin/unauthorized.js"]}]}.children,I=["/app/app/login/page.js"],J={require:c,loadChunk:()=>Promise.resolve()},K=new d.AppPageRouteModule({definition:{kind:e.RouteKind.APP_PAGE,page:"/login/page",pathname:"/login",bundlePath:"",filename:"",appPaths:[]},userland:{loaderTree:H},distDir:".next",relativeProjectDir:""});async function L(a,b,d){var C;let G="/login/page";"/index"===G&&(G="/");let M=(0,h.getRequestMeta)(a,"postponed"),N=(0,h.getRequestMeta)(a,"minimalMode"),O=await K.prepare(a,b,{srcPage:G,multiZoneDraftMode:!1});if(!O)return b.statusCode=400,b.end("Bad Request"),null==d.waitUntil||d.waitUntil.call(d,Promise.resolve()),null;let{buildId:P,query:Q,params:R,parsedUrl:S,pageIsDynamic:T,buildManifest:U,nextFontManifest:V,reactLoadableManifest:W,serverActionsManifest:X,clientReferenceManifest:Y,subresourceIntegrityManifest:Z,prerenderManifest:$,isDraftMode:_,resolvedPathname:aa,revalidateOnlyGenerated:ab,routerServerContext:ac,nextConfig:ad,interceptionRoutePatterns:ae}=O,af=S.pathname||"/",ag=(0,r.normalizeAppPath)(G),{isOnDemandRevalidate:ah}=O,ai=K.match(af,$),aj=!!$.routes[aa],ak=!!(ai||aj||$.routes[ag]),al=a.headers["user-agent"]||"",am=(0,u.getBotType)(al),an=(0,p.isHtmlBotRequest)(a),ao=(0,h.getRequestMeta)(a,"isPrefetchRSCRequest")??"1"===a.headers[t.NEXT_ROUTER_PREFETCH_HEADER],ap=(0,h.getRequestMeta)(a,"isRSCRequest")??!!a.headers[t.RSC_HEADER],aq=(0,s.getIsPossibleServerAction)(a),ar=(0,m.checkIsAppPPREnabled)(ad.experimental.ppr)&&(null==(C=$.routes[ag]??$.dynamicRoutes[ag])?void 0:C.renderingMode)==="PARTIALLY_STATIC",as=!1,at=!1,au=ar?M:void 0,av=ar&&ap&&!ao,aw=(0,h.getRequestMeta)(a,"segmentPrefetchRSCRequest"),ax=!al||(0,p.shouldServeStreamingMetadata)(al,ad.htmlLimitedBots);an&&ar&&(ak=!1,ax=!1);let ay=!0===K.isDev||!ak||"string"==typeof M||av,az=an&&ar,aA=null;_||!ak||ay||aq||au||av||(aA=aa);let aB=aA;!aB&&K.isDev&&(aB=aa),K.isDev||_||!ak||!ap||av||(0,k.d)(a.headers);let aC={...E,tree:H,pages:I,GlobalError:D(),handler:L,routeModule:K,__next_app__:J};X&&Y&&(0,o.setReferenceManifestsSingleton)({page:G,clientReferenceManifest:Y,serverActionsManifest:X,serverModuleMap:(0,q.createServerModuleMap)({serverActionsManifest:X})});let aD=a.method||"GET",aE=(0,g.getTracer)(),aF=aE.getActiveScopeSpan();try{let f=K.getVaryHeader(aa,ae);b.setHeader("Vary",f);let k=async(c,d)=>{let e=new l.NodeNextRequest(a),f=new l.NodeNextResponse(b);return K.render(e,f,d).finally(()=>{if(!c)return;c.setAttributes({"http.status_code":b.statusCode,"next.rsc":!1});let d=aE.getRootSpanAttributes();if(!d)return;if(d.get("next.span_type")!==i.BaseServerSpan.handleRequest)return void console.warn(`Unexpected root span type '${d.get("next.span_type")}'. Please report this Next.js issue https://github.com/vercel/next.js`);let e=d.get("next.route");if(e){let a=`${aD} ${e}`;c.setAttributes({"next.route":e,"http.route":e,"next.span_name":a}),c.updateName(a)}else c.updateName(`${aD} ${a.url}`)})},m=async({span:e,postponed:f,fallbackRouteParams:g})=>{let i={query:Q,params:R,page:ag,sharedContext:{buildId:P},serverComponentsHmrCache:(0,h.getRequestMeta)(a,"serverComponentsHmrCache"),fallbackRouteParams:g,renderOpts:{App:()=>null,Document:()=>null,pageConfig:{},ComponentMod:aC,Component:(0,j.T)(aC),params:R,routeModule:K,page:G,postponed:f,shouldWaitOnAllReady:az,serveStreamingMetadata:ax,supportsDynamicResponse:"string"==typeof f||ay,buildManifest:U,nextFontManifest:V,reactLoadableManifest:W,subresourceIntegrityManifest:Z,serverActionsManifest:X,clientReferenceManifest:Y,setIsrStatus:null==ac?void 0:ac.setIsrStatus,dir:c(3873).join(process.cwd(),K.relativeProjectDir),isDraftMode:_,isRevalidate:ak&&!f&&!av,botType:am,isOnDemandRevalidate:ah,isPossibleServerAction:aq,assetPrefix:ad.assetPrefix,nextConfigOutput:ad.output,crossOrigin:ad.crossOrigin,trailingSlash:ad.trailingSlash,previewProps:$.preview,deploymentId:ad.deploymentId,enableTainting:ad.experimental.taint,htmlLimitedBots:ad.htmlLimitedBots,devtoolSegmentExplorer:ad.experimental.devtoolSegmentExplorer,reactMaxHeadersLength:ad.reactMaxHeadersLength,multiZoneDraftMode:!1,incrementalCache:(0,h.getRequestMeta)(a,"incrementalCache"),cacheLifeProfiles:ad.experimental.cacheLife,basePath:ad.basePath,serverActions:ad.experimental.serverActions,...as?{nextExport:!0,supportsDynamicResponse:!1,isStaticGeneration:!0,isRevalidate:!0,isDebugDynamicAccesses:as}:{},experimental:{isRoutePPREnabled:ar,expireTime:ad.expireTime,staleTimes:ad.experimental.staleTimes,cacheComponents:!!ad.experimental.cacheComponents,clientSegmentCache:!!ad.experimental.clientSegmentCache,clientParamParsing:!!ad.experimental.clientParamParsing,dynamicOnHover:!!ad.experimental.dynamicOnHover,inlineCss:!!ad.experimental.inlineCss,authInterrupts:!!ad.experimental.authInterrupts,clientTraceMetadata:ad.experimental.clientTraceMetadata||[]},waitUntil:d.waitUntil,onClose:a=>{b.on("close",a)},onAfterTaskError:()=>{},onInstrumentationRequestError:(b,c,d)=>K.onRequestError(a,b,d,ac),err:(0,h.getRequestMeta)(a,"invokeError"),dev:K.isDev}},l=await k(e,i),{metadata:m}=l,{cacheControl:n,headers:o={},fetchTags:p}=m;if(p&&(o[y.NEXT_CACHE_TAGS_HEADER]=p),a.fetchMetrics=m.fetchMetrics,ak&&(null==n?void 0:n.revalidate)===0&&!K.isDev&&!ar){let a=m.staticBailoutInfo,b=Object.defineProperty(Error(`Page changed from static to dynamic at runtime ${aa}${(null==a?void 0:a.description)?`, reason: ${a.description}`:""}
see more here https://nextjs.org/docs/messages/app-static-to-dynamic-error`),"__NEXT_ERROR_CODE",{value:"E132",enumerable:!1,configurable:!0});if(null==a?void 0:a.stack){let c=a.stack;b.stack=b.message+c.substring(c.indexOf("\n"))}throw b}return{value:{kind:v.CachedRouteKind.APP_PAGE,html:l,headers:o,rscData:m.flightData,postponed:m.postponed,status:m.statusCode,segmentData:m.segmentData},cacheControl:n}},o=async({hasResolved:c,previousCacheEntry:f,isRevalidating:g,span:i})=>{let j,k=!1===K.isDev,l=c||b.writableEnded;if(ah&&ab&&!f&&!N)return(null==ac?void 0:ac.render404)?await ac.render404(a,b):(b.statusCode=404,b.end("This page could not be found")),null;if(ai&&(j=(0,w.parseFallbackField)(ai.fallback)),j===w.FallbackMode.PRERENDER&&(0,u.isBot)(al)&&(!ar||an)&&(j=w.FallbackMode.BLOCKING_STATIC_RENDER),(null==f?void 0:f.isStale)===-1&&(ah=!0),ah&&(j!==w.FallbackMode.NOT_FOUND||f)&&(j=w.FallbackMode.BLOCKING_STATIC_RENDER),!N&&j!==w.FallbackMode.BLOCKING_STATIC_RENDER&&aB&&!l&&!_&&T&&(k||!aj)){let b;if((k||ai)&&j===w.FallbackMode.NOT_FOUND)throw new B.NoFallbackError;if(ar&&!ap){let c="string"==typeof(null==ai?void 0:ai.fallback)?ai.fallback:k?ag:null;if(b=await K.handleResponse({cacheKey:c,req:a,nextConfig:ad,routeKind:e.RouteKind.APP_PAGE,isFallback:!0,prerenderManifest:$,isRoutePPREnabled:ar,responseGenerator:async()=>m({span:i,postponed:void 0,fallbackRouteParams:k||at?(0,n.u)(ag):null}),waitUntil:d.waitUntil}),null===b)return null;if(b)return delete b.cacheControl,b}}let o=ah||g||!au?void 0:au;if(as&&void 0!==o)return{cacheControl:{revalidate:1,expire:void 0},value:{kind:v.CachedRouteKind.PAGES,html:x.default.EMPTY,pageData:{},headers:void 0,status:void 0}};let p=T&&ar&&((0,h.getRequestMeta)(a,"renderFallbackShell")||at)?(0,n.u)(af):null;return m({span:i,postponed:o,fallbackRouteParams:p})},p=async c=>{var f,g,i,j,k;let l,n=await K.handleResponse({cacheKey:aA,responseGenerator:a=>o({span:c,...a}),routeKind:e.RouteKind.APP_PAGE,isOnDemandRevalidate:ah,isRoutePPREnabled:ar,req:a,nextConfig:ad,prerenderManifest:$,waitUntil:d.waitUntil});if(_&&b.setHeader("Cache-Control","private, no-cache, no-store, max-age=0, must-revalidate"),K.isDev&&b.setHeader("Cache-Control","no-store, must-revalidate"),!n){if(aA)throw Object.defineProperty(Error("invariant: cache entry required but not generated"),"__NEXT_ERROR_CODE",{value:"E62",enumerable:!1,configurable:!0});return null}if((null==(f=n.value)?void 0:f.kind)!==v.CachedRouteKind.APP_PAGE)throw Object.defineProperty(Error(`Invariant app-page handler received invalid cache entry ${null==(i=n.value)?void 0:i.kind}`),"__NEXT_ERROR_CODE",{value:"E707",enumerable:!1,configurable:!0});let p="string"==typeof n.value.postponed;ak&&!av&&(!p||ao)&&(N||b.setHeader("x-nextjs-cache",ah?"REVALIDATED":n.isMiss?"MISS":n.isStale?"STALE":"HIT"),b.setHeader(t.NEXT_IS_PRERENDER_HEADER,"1"));let{value:q}=n;if(au)l={revalidate:0,expire:void 0};else if(N&&ap&&!ao&&ar)l={revalidate:0,expire:void 0};else if(!K.isDev)if(_)l={revalidate:0,expire:void 0};else if(ak){if(n.cacheControl)if("number"==typeof n.cacheControl.revalidate){if(n.cacheControl.revalidate<1)throw Object.defineProperty(Error(`Invalid revalidate configuration provided: ${n.cacheControl.revalidate} < 1`),"__NEXT_ERROR_CODE",{value:"E22",enumerable:!1,configurable:!0});l={revalidate:n.cacheControl.revalidate,expire:(null==(j=n.cacheControl)?void 0:j.expire)??ad.expireTime}}else l={revalidate:y.CACHE_ONE_YEAR,expire:void 0}}else b.getHeader("Cache-Control")||(l={revalidate:0,expire:void 0});if(n.cacheControl=l,"string"==typeof aw&&(null==q?void 0:q.kind)===v.CachedRouteKind.APP_PAGE&&q.segmentData){b.setHeader(t.NEXT_DID_POSTPONE_HEADER,"2");let c=null==(k=q.headers)?void 0:k[y.NEXT_CACHE_TAGS_HEADER];N&&ak&&c&&"string"==typeof c&&b.setHeader(y.NEXT_CACHE_TAGS_HEADER,c);let d=q.segmentData.get(aw);return void 0!==d?(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:x.default.fromStatic(d,t.RSC_CONTENT_TYPE_HEADER),cacheControl:n.cacheControl}):(b.statusCode=204,(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:x.default.EMPTY,cacheControl:n.cacheControl}))}let r=(0,h.getRequestMeta)(a,"onCacheEntry");if(r&&await r({...n,value:{...n.value,kind:"PAGE"}},{url:(0,h.getRequestMeta)(a,"initURL")}))return null;if(p&&au)throw Object.defineProperty(Error("Invariant: postponed state should not be present on a resume request"),"__NEXT_ERROR_CODE",{value:"E396",enumerable:!1,configurable:!0});if(q.headers){let a={...q.headers};for(let[c,d]of(N&&ak||delete a[y.NEXT_CACHE_TAGS_HEADER],Object.entries(a)))if(void 0!==d)if(Array.isArray(d))for(let a of d)b.appendHeader(c,a);else"number"==typeof d&&(d=d.toString()),b.appendHeader(c,d)}let s=null==(g=q.headers)?void 0:g[y.NEXT_CACHE_TAGS_HEADER];if(N&&ak&&s&&"string"==typeof s&&b.setHeader(y.NEXT_CACHE_TAGS_HEADER,s),!q.status||ap&&ar||(b.statusCode=q.status),!N&&q.status&&F.RedirectStatusCode[q.status]&&ap&&(b.statusCode=200),p&&b.setHeader(t.NEXT_DID_POSTPONE_HEADER,"1"),ap&&!_){if(void 0===q.rscData){if(q.postponed)throw Object.defineProperty(Error("Invariant: Expected postponed to be undefined"),"__NEXT_ERROR_CODE",{value:"E372",enumerable:!1,configurable:!0});return(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:q.html,cacheControl:av?{revalidate:0,expire:void 0}:n.cacheControl})}return(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:x.default.fromStatic(q.rscData,t.RSC_CONTENT_TYPE_HEADER),cacheControl:n.cacheControl})}let u=q.html;if(!p||N||ap)return(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:u,cacheControl:n.cacheControl});if(as)return u.push(new ReadableStream({start(a){a.enqueue(z.ENCODED_TAGS.CLOSED.BODY_AND_HTML),a.close()}})),(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:u,cacheControl:{revalidate:0,expire:void 0}});let w=new TransformStream;return u.push(w.readable),m({span:c,postponed:q.postponed,fallbackRouteParams:null}).then(async a=>{var b,c;if(!a)throw Object.defineProperty(Error("Invariant: expected a result to be returned"),"__NEXT_ERROR_CODE",{value:"E463",enumerable:!1,configurable:!0});if((null==(b=a.value)?void 0:b.kind)!==v.CachedRouteKind.APP_PAGE)throw Object.defineProperty(Error(`Invariant: expected a page response, got ${null==(c=a.value)?void 0:c.kind}`),"__NEXT_ERROR_CODE",{value:"E305",enumerable:!1,configurable:!0});await a.value.html.pipeTo(w.writable)}).catch(a=>{w.writable.abort(a).catch(a=>{console.error("couldn't abort transformer",a)})}),(0,A.sendRenderResult)({req:a,res:b,generateEtags:ad.generateEtags,poweredByHeader:ad.poweredByHeader,result:u,cacheControl:{revalidate:0,expire:void 0}})};if(!aF)return await aE.withPropagatedContext(a.headers,()=>aE.trace(i.BaseServerSpan.handleRequest,{spanName:`${aD} ${a.url}`,kind:g.SpanKind.SERVER,attributes:{"http.method":aD,"http.target":a.url}},p));await p(aF)}catch(b){throw b instanceof B.NoFallbackError||await K.onRequestError(a,b,{routerKind:"App Router",routePath:G,routeType:"render",revalidateReason:(0,f.c)({isRevalidate:ak,isOnDemandRevalidate:ah})},ac),b}}},7012:(a,b,c)=>{"use strict";function d(){return"dark"}function e(a){return"undefined"==typeof document||(document.documentElement.dataset.theme=a,window.localStorage.setItem("mcp-theme",a)),a}function f(a){return"light"===a?"dark":"light"}c.d(b,{AZ:()=>e,jC:()=>f,zf:()=>d})},7404:(a,b,c)=>{Promise.resolve().then(c.t.bind(c,4160,23)),Promise.resolve().then(c.t.bind(c,1603,23)),Promise.resolve().then(c.t.bind(c,8495,23)),Promise.resolve().then(c.t.bind(c,5170,23)),Promise.resolve().then(c.t.bind(c,7526,23)),Promise.resolve().then(c.t.bind(c,8922,23)),Promise.resolve().then(c.t.bind(c,9234,23)),Promise.resolve().then(c.t.bind(c,2263,23)),Promise.resolve().then(c.bind(c,2146))},7697:(a,b,c)=>{"use strict";c.r(b),c.d(b,{default:()=>h,metadata:()=>g});var d=c(5338),e=c(1533),f=c.n(e);c(2704);let g={title:"MCP Platform",description:"MCP hosting platform dashboard"};function h({children:a}){return(0,d.jsx)("html",{lang:"en",suppressHydrationWarning:!0,children:(0,d.jsxs)("body",{className:f().variable,suppressHydrationWarning:!0,children:[(0,d.jsx)("script",{dangerouslySetInnerHTML:{__html:`
              (() => {
                try {
                  const key = "mcp-theme";
                  const stored = window.localStorage.getItem(key);
                  const theme =
                    stored === "light" || stored === "dark"
                      ? stored
                      : (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
                  document.documentElement.dataset.theme = theme;
                } catch (error) {
                  document.documentElement.dataset.theme = "dark";
                }
              })();
            `}}),a]})})}},8354:a=>{"use strict";a.exports=require("util")},8825:(a,b,c)=>{Promise.resolve().then(c.bind(c,5290))},9121:a=>{"use strict";a.exports=require("next/dist/server/app-render/action-async-storage.external.js")},9294:a=>{"use strict";a.exports=require("next/dist/server/app-render/work-async-storage.external.js")},9414:()=>{}};var b=require("../../webpack-runtime.js");b.C(a);var c=b.X(0,[70],()=>b(b.s=6773));module.exports=c})();