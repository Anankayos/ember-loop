package it.emberloop.terminale;

import android.Manifest;
import android.annotation.SuppressLint;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import androidx.activity.OnBackPressedCallback;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.webkit.WebViewAssetLoader;

/**
 * Un guscio intorno all'app, che resta la stessa pagina sola di sempre.
 *
 * Il punto di tutto e' WebViewAssetLoader: serve gli assets sotto
 * https://appassets.androidplatform.net/ , che per il WebView e' un'origine SICURA.
 * Da li' getUserMedia funziona, e quindi lo scanner QR funziona - cosa che da
 * http://192.168.x.x non succede e da un file:// nemmeno.
 *
 * Nessun accesso alla rete: il manifest non chiede INTERNET e il loader non esce
 * dagli assets. Se una richiesta non e' nostra, si rifiuta invece di passare oltre.
 */
public class MainActivity extends AppCompatActivity {

    private static final int CHIEDO_FOTOCAMERA = 1;
    private WebView web;
    private PermissionRequest inAttesa;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle stato) {
        super.onCreate(stato);

        final WebViewAssetLoader loader = new WebViewAssetLoader.Builder()
                .addPathHandler("/assets/", new WebViewAssetLoader.AssetsPathHandler(this))
                .build();

        web = new WebView(this);
        // Cinque ore con il telefono sul tavolo: se lo schermo si spegne ogni trenta
        // secondi si passa la serata a sbloccarlo. Non serve nessun permesso, e' un
        // flag della vista; la pagina prova anche da sola con l'API Wake Lock, che
        // nel WebView non c'e' sempre.
        web.setKeepScreenOn(true);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);          // localStorage: e' li' che sta lo stato del giocatore
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setCacheMode(WebSettings.LOAD_NO_CACHE);
        s.setTextZoom(100);                    // la dimensione del testo di sistema non sfonda il layout

        web.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView v, WebResourceRequest req) {
                return loader.shouldInterceptRequest(req.getUrl());
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest req) {
                // niente esce da qui: l'app non ha nemmeno il permesso di rete
                Uri u = req.getUrl();
                return !"appassets.androidplatform.net".equals(u.getHost());
            }

            // Una pagina bianca senza spiegazione e' il peggio che possa capitare la sera
            // della partita: se il caricamento fallisce si dice cosa e' successo.
            @Override
            public void onReceivedError(WebView v, WebResourceRequest req, android.webkit.WebResourceError err) {
                if (!req.isForMainFrame()) return;
                mostraGuasto("Il terminale non si e' aperto",
                        err.getDescription() + " (codice " + err.getErrorCode() + ")",
                        req.getUrl().toString());
            }

            @Override
            public void onReceivedHttpError(WebView v, WebResourceRequest req, WebResourceResponse resp) {
                if (!req.isForMainFrame()) return;
                mostraGuasto("Il terminale non si e' aperto",
                        "risposta " + resp.getStatusCode(), req.getUrl().toString());
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest richiesta) {
                runOnUiThread(() -> {
                    boolean vuoleCamera = false;
                    for (String r : richiesta.getResources()) {
                        if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(r)) vuoleCamera = true;
                    }
                    if (!vuoleCamera) { richiesta.deny(); return; }
                    if (ContextCompat.checkSelfPermission(MainActivity.this, Manifest.permission.CAMERA)
                            == PackageManager.PERMISSION_GRANTED) {
                        richiesta.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
                    } else {
                        // il permesso di sistema non c'e' ancora: lo si chiede e si risponde dopo
                        inAttesa = richiesta;
                        ActivityCompat.requestPermissions(MainActivity.this,
                                new String[]{Manifest.permission.CAMERA}, CHIEDO_FOTOCAMERA);
                    }
                });
            }
        });

        // il tasto Indietro torna indietro nell'app, e solo in fondo chiude
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (web.canGoBack()) web.goBack();
                else { setEnabled(false); getOnBackPressedDispatcher().onBackPressed(); }
            }
        });

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            web.setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
        }
        if (stato == null) {
            web.loadUrl("https://appassets.androidplatform.net/assets/index.html");
        } else {
            web.restoreState(stato);
        }
    }

    /** Il guasto scritto sullo schermo, nello stesso scuro della pagina. */
    private void mostraGuasto(String titolo, String perche, String dove) {
        String html =
                "<!doctype html><meta charset='utf-8'>"
              + "<meta name='viewport' content='width=device-width,initial-scale=1'>"
              + "<style>body{margin:0;padding:28px 20px;background:#0B0C10;color:#E8E6E1;"
              + "font:15px/1.6 system-ui,sans-serif}h1{font-size:19px;margin:0 0 14px;color:#F08A4B}"
              + "code{font-family:ui-monospace,monospace;font-size:13px;color:#9AA0B4;"
              + "display:block;margin:10px 0;word-break:break-all}"
              + "p{margin:0 0 12px}.n{color:#9AA0B4;font-size:13px}</style>"
              + "<h1>" + fuggi(titolo) + "</h1>"
              + "<p>" + fuggi(perche) + "</p><code>" + fuggi(dove) + "</code>"
              + "<p class='n'>Riferiscilo com'e'. Se dice qualcosa come "
              + "<b>ERR_ACCESS_DENIED</b> o <b>net::ERR_</b>, il guscio non riesce a leggere "
              + "gli assets e si sistema in una riga.</p>";
        runOnUiThread(() -> web.loadDataWithBaseURL(null, html, "text/html", "UTF-8", null));
    }

    private static String fuggi(String s) {
        return s == null ? "" : s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }

    @Override
    public void onRequestPermissionsResult(int codice, String[] permessi, int[] esiti) {
        super.onRequestPermissionsResult(codice, permessi, esiti);
        if (codice != CHIEDO_FOTOCAMERA || inAttesa == null) return;
        boolean dato = esiti.length > 0 && esiti[0] == PackageManager.PERMISSION_GRANTED;
        // Negare esplicitamente e' importante: l'app mostra "Fotocamera: permesso negato"
        // invece di restare in silenzio, e il codice del sigillo si puo' digitare.
        if (dato) inAttesa.grant(new String[]{PermissionRequest.RESOURCE_VIDEO_CAPTURE});
        else inAttesa.deny();
        inAttesa = null;
    }

    @Override
    protected void onSaveInstanceState(Bundle fuori) {
        super.onSaveInstanceState(fuori);
        web.saveState(fuori);
    }

    @Override
    protected void onDestroy() {
        if (web != null) web.destroy();
        super.onDestroy();
    }
}
