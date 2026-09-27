/**
 * Resonance Sound Studio — Minimalist Music Workstation
 * Architecture: Clean Vanilla SPA with reactive state
 */

// Application State
const state = {
  currentUser: null,
  currentPath: "",
  treeData: null,
  currentListing: null,
  filteredFiles: [],
  selectedPaths: new Set(),
  activeFormatFilter: "ALL",
  searchQuery: "",
  activeView: "explorer", // "explorer" | "editor" | "uploads"
  
  // Editor State
  editorTrackPath: null,
  editorOriginalData: null,
  editorDirTracks: [],
  editorModified: false,
  waveformPeaks: [],
  
  // Audio Player State
  isPlaying: false,
  playingPath: null,
  
  // Upload Queue State
  uploadQueue: [],
  isUploading: false,
};

// DOM Cache
const dom = {};

document.addEventListener("DOMContentLoaded", () => {
  initDom();
  initEvents();
  checkAuth();
});

function initDom() {
  dom.authScreen = document.getElementById("authScreen");
  dom.loginForm = document.getElementById("loginForm");
  dom.loginUsername = document.getElementById("loginUsername");
  dom.loginPassword = document.getElementById("loginPassword");
  dom.loginError = document.getElementById("loginError");
  dom.usernameDisplay = document.getElementById("usernameDisplay");
  dom.userInitial = document.getElementById("userInitial");
  dom.logoutBtn = document.getElementById("logoutBtn");

  dom.viewExplorer = document.getElementById("viewExplorer");
  dom.viewTagEditor = document.getElementById("viewTagEditor");
  dom.viewUploads = document.getElementById("viewUploads");

  dom.navExplorer = document.getElementById("navExplorer");
  dom.navTagEditor = document.getElementById("navTagEditor");
  dom.navUploads = document.getElementById("navUploads");

  dom.headerBreadcrumbs = document.getElementById("headerBreadcrumbs");
  dom.explorerBreadcrumbs = document.getElementById("explorerBreadcrumbs");
  dom.currentFolderTitle = document.getElementById("currentFolderTitle");
  dom.currentFolderStats = document.getElementById("currentFolderStats");
  dom.directoryTreeContainer = document.getElementById("directoryTreeContainer");
  dom.fileTableBody = document.getElementById("fileTableBody");
  dom.emptyFolderState = document.getElementById("emptyFolderState");
  dom.btnParentFolder = document.getElementById("btnParentFolder");
  dom.selectAllCheckbox = document.getElementById("selectAllCheckbox");
  dom.globalSearch = document.getElementById("globalSearch");
  dom.formatFilterBar = document.getElementById("formatFilterBar");
  dom.selectionActions = document.getElementById("selectionActions");
  dom.selectedCount = document.getElementById("selectedCount");

  // Modals
  dom.modalNewFolder = document.getElementById("modalNewFolder");
  dom.modalRename = document.getElementById("modalRename");
  dom.modalMove = document.getElementById("modalMove");
  dom.modalDelete = document.getElementById("modalDelete");
  dom.modalBatchTag = document.getElementById("modalBatchTag");
  dom.toastContainer = document.getElementById("toastContainer");

  // Editor DOM
  dom.editorTrackSwitcher = document.getElementById("editorTrackSwitcher");
  dom.editorTrackPosition = document.getElementById("editorTrackPosition");
  dom.editorFormatTag = document.getElementById("editorFormatTag");
  dom.unsavedChangesBadge = document.getElementById("unsavedChangesBadge");
  dom.unsavedCount = document.getElementById("unsavedCount");
  dom.btnSaveTags = document.getElementById("btnSaveTags");
  dom.btnRevertTags = document.getElementById("btnRevertTags");
  dom.metadataForm = document.getElementById("metadataForm");

  dom.metaTitle = document.getElementById("metaTitle");
  dom.metaArtist = document.getElementById("metaArtist");
  dom.metaAlbumArtist = document.getElementById("metaAlbumArtist");
  dom.metaAlbum = document.getElementById("metaAlbum");
  dom.metaYear = document.getElementById("metaYear");
  dom.metaTrackNumber = document.getElementById("metaTrackNumber");
  dom.metaTrackTotal = document.getElementById("metaTrackTotal");
  dom.metaDiscNumber = document.getElementById("metaDiscNumber");
  dom.metaDiscTotal = document.getElementById("metaDiscTotal");
  dom.metaGenre = document.getElementById("metaGenre");
  dom.metaComposer = document.getElementById("metaComposer");
  dom.metaComment = document.getElementById("metaComment");

  // Artwork DOM
  dom.editorArtworkImg = document.getElementById("editorArtworkImg");
  dom.artworkPlaceholder = document.getElementById("artworkPlaceholder");
  dom.artworkSpecPill = document.getElementById("artworkSpecPill");
  dom.artworkFormat = document.getElementById("artworkFormat");
  dom.artworkDimensions = document.getElementById("artworkDimensions");
  dom.artworkSize = document.getElementById("artworkSize");
  dom.artworkFileInput = document.getElementById("artworkFileInput");
  dom.btnRemoveArtwork = document.getElementById("btnRemoveArtwork");

  // Audio Player DOM
  dom.globalAudioPlayer = document.getElementById("globalAudioPlayer");
  dom.playerPlayPauseBtn = document.getElementById("playerPlayPauseBtn");
  dom.playerPlayIcon = document.getElementById("playerPlayIcon");
  dom.playerCurrentTime = document.getElementById("playerCurrentTime");
  dom.playerTotalTime = document.getElementById("playerTotalTime");
  dom.waveformContainer = document.getElementById("waveformContainer");
  dom.waveformBars = document.getElementById("waveformBars");
  dom.waveformPlayhead = document.getElementById("waveformPlayhead");
  dom.playerVolumeSlider = document.getElementById("playerVolumeSlider");
  dom.playerMuteBtn = document.getElementById("playerMuteBtn");
  dom.playerVolumeIcon = document.getElementById("playerVolumeIcon");
  dom.playerCodecBadge = document.getElementById("playerCodecBadge");

  // Specs DOM
  dom.specLosslessPill = document.getElementById("specLosslessPill");
  dom.specBitrate = document.getElementById("specBitrate");
  dom.specSampleRate = document.getElementById("specSampleRate");
  dom.specBitDepth = document.getElementById("specBitDepth");
  dom.specChannels = document.getElementById("specChannels");
  dom.specCodec = document.getElementById("specCodec");
  dom.specFileSize = document.getElementById("specFileSize");

  // Upload Queue DOM
  dom.dropZone = document.getElementById("dropZone");
  dom.fileUploadInput = document.getElementById("fileUploadInput");
  dom.uploadTargetFolderSelect = document.getElementById("uploadTargetFolderSelect");
  dom.queueTableBody = document.getElementById("queueTableBody");
  dom.queueCountBadge = document.getElementById("queueCountBadge");
  dom.uploadBadge = document.getElementById("uploadBadge");
  dom.btnStartUpload = document.getElementById("btnStartUpload");
  dom.btnClearQueue = document.getElementById("btnClearQueue");
}

function initEvents() {
  // Navigation tabs
  dom.navExplorer.addEventListener("click", () => switchView("explorer"));
  dom.navTagEditor.addEventListener("click", () => {
    if (state.editorTrackPath) {
      switchView("editor");
    } else {
      // Find first audio file in current directory if available
      const firstAudio = state.currentListing?.files?.find(f => f.is_audio);
      if (firstAudio) {
        openTagEditor(firstAudio.path);
      } else {
        showToast("Select an audio track to edit metadata", "info");
      }
    }
  });
  dom.navUploads.addEventListener("click", () => switchView("uploads"));

  // Auth
  dom.loginForm.addEventListener("submit", handleLoginSubmit);
  dom.logoutBtn.addEventListener("click", handleLogout);

  // Search & Filter
  dom.globalSearch.addEventListener("input", (e) => {
    state.searchQuery = e.target.value.toLowerCase();
    applyFileFilters();
  });
  window.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      dom.globalSearch.focus();
    }
  });

  dom.formatFilterBar.addEventListener("click", (e) => {
    const pill = e.target.closest(".filter-pill");
    if (!pill) return;
    document.querySelectorAll(".filter-pill").forEach(p => {
      p.className = "filter-pill px-2.5 py-1 rounded text-slate-600 hover:text-slate-900 transition-colors";
    });
    pill.className = "filter-pill px-2.5 py-1 rounded bg-white text-primary font-semibold shadow-xs transition-all";
    state.activeFormatFilter = pill.getAttribute("data-format");
    applyFileFilters();
  });

  // Table selection
  dom.selectAllCheckbox.addEventListener("change", (e) => {
    const checked = e.target.checked;
    state.selectedPaths.clear();
    if (checked) {
      state.filteredFiles.forEach(f => state.selectedPaths.add(f.path));
    }
    updateSelectionUI();
    renderFileList();
  });

  // Actions
  document.getElementById("btnNewFolder").addEventListener("click", () => openModal("modalNewFolder"));
  document.getElementById("btnUploadModal").addEventListener("click", () => {
    switchView("uploads");
    dom.uploadTargetFolderSelect.value = state.currentPath;
  });
  dom.btnParentFolder.addEventListener("click", () => {
    if (state.currentListing && state.currentListing.parent_path !== null) {
      navigateToFolder(state.currentListing.parent_path);
    }
  });

  // Batch actions
  document.getElementById("batchTagBtn").addEventListener("click", openBatchTagModal);
  document.getElementById("batchMoveBtn").addEventListener("click", () => openMoveModal(Array.from(state.selectedPaths)));
  document.getElementById("batchDeleteBtn").addEventListener("click", () => openDeleteModal(Array.from(state.selectedPaths)));

  // Forms
  document.getElementById("newFolderForm").addEventListener("submit", handleCreateFolder);
  document.getElementById("renameForm").addEventListener("submit", handleRenameSubmit);
  document.getElementById("moveForm").addEventListener("submit", handleMoveSubmit);
  document.getElementById("batchTagForm").addEventListener("submit", handleBatchTagSubmit);
  document.getElementById("btnConfirmDelete").addEventListener("click", handleConfirmDelete);

  // Editor Actions
  dom.editorTrackSwitcher.addEventListener("change", (e) => {
    openTagEditor(e.target.value);
  });
  dom.btnSaveTags.addEventListener("click", handleSaveTags);
  dom.btnRevertTags.addEventListener("click", handleRevertTags);
  dom.metadataForm.addEventListener("input", checkEditorDirty);

  // Artwork
  dom.artworkFileInput.addEventListener("change", handleArtworkUpload);
  dom.btnRemoveArtwork.addEventListener("click", handleRemoveArtwork);

  // Audio Player Events
  dom.playerPlayPauseBtn.addEventListener("click", toggleAudioPlayback);
  dom.globalAudioPlayer.addEventListener("timeupdate", updatePlayerProgress);
  dom.globalAudioPlayer.addEventListener("loadedmetadata", onAudioLoaded);
  dom.globalAudioPlayer.addEventListener("ended", () => {
    state.isPlaying = false;
    dom.playerPlayIcon.textContent = "play_arrow";
    updateWaveformDisplay(0);
    renderFileList();
  });
  dom.waveformContainer.addEventListener("click", handleWaveformSeek);
  dom.playerVolumeSlider.addEventListener("input", (e) => {
    dom.globalAudioPlayer.volume = parseFloat(e.target.value);
    dom.playerVolumeIcon.textContent = e.target.value > 0 ? "volume_up" : "volume_off";
  });
  dom.playerMuteBtn.addEventListener("click", () => {
    dom.globalAudioPlayer.muted = !dom.globalAudioPlayer.muted;
    dom.playerVolumeIcon.textContent = dom.globalAudioPlayer.muted ? "volume_off" : "volume_up";
  });

  // Drag & Drop Ingestion
  dom.dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dom.dropZone.classList.add("border-teal-500", "bg-teal-50/40");
  });
  dom.dropZone.addEventListener("dragleave", () => {
    dom.dropZone.classList.remove("border-teal-500", "bg-teal-50/40");
  });
  dom.dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dom.dropZone.classList.remove("border-teal-500", "bg-teal-50/40");
    if (e.dataTransfer.files.length > 0) {
      addFilesToUploadQueue(e.dataTransfer.files);
    }
  });
  dom.fileUploadInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      addFilesToUploadQueue(e.target.files);
    }
  });
  dom.btnStartUpload.addEventListener("click", startBatchUpload);
  dom.btnClearQueue.addEventListener("click", clearUploadQueue);
}

// ==========================================================================
// Authentication
// ==========================================================================

async function checkAuth() {
  try {
    const res = await fetch("/api/auth/me");
    if (res.ok) {
      const data = await res.json();
      setAuthenticated(data.username);
    } else {
      showAuthScreen();
    }
  } catch (err) {
    showAuthScreen();
  }
}

function showAuthScreen() {
  dom.authScreen.classList.remove("hidden");
  dom.loginUsername.focus();
}

function setAuthenticated(username) {
  state.currentUser = username;
  dom.authScreen.classList.add("hidden");
  dom.usernameDisplay.textContent = username;
  dom.userInitial.textContent = username.charAt(0).toUpperCase();

  // Load workstation data
  reloadTree();
  navigateToFolder(state.currentPath);
}

async function handleLoginSubmit(e) {
  e.preventDefault();
  dom.loginError.classList.add("hidden");

  const username = dom.loginUsername.value.trim();
  const password = dom.loginPassword.value;

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (res.ok) {
      const data = await res.json();
      setAuthenticated(data.username);
      showToast(`Welcome back, ${data.username}`, "success");
    } else {
      dom.loginError.classList.remove("hidden");
    }
  } catch (err) {
    dom.loginError.classList.remove("hidden");
  }
}

async function handleLogout() {
  try {
    await fetch("/api/auth/logout", { method: "POST" });
  } catch (err) {}
  state.currentUser = null;
  state.isPlaying = false;
  dom.globalAudioPlayer.pause();
  showAuthScreen();
}

// ==========================================================================
// Workstation Navigation & View Switching
// ==========================================================================

function switchView(viewName) {
  state.activeView = viewName;
  dom.viewExplorer.classList.toggle("hidden", viewName !== "explorer");
  dom.viewTagEditor.classList.toggle("hidden", viewName !== "editor");
  dom.viewUploads.classList.toggle("hidden", viewName !== "uploads");

  // Update nav rail active style
  const activeClass = "group relative flex items-center justify-center w-10 h-10 rounded-xl transition-all bg-primary text-white shadow-sm shadow-teal-600/20";
  const inactiveClass = "group relative flex items-center justify-center w-10 h-10 rounded-xl text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition-all";

  dom.navExplorer.className = viewName === "explorer" ? activeClass : inactiveClass;
  dom.navTagEditor.className = viewName === "editor" ? activeClass : inactiveClass;
  dom.navUploads.className = viewName === "uploads" ? activeClass : inactiveClass;
}

// ==========================================================================
// Directory Tree & Folder Browsing
// ==========================================================================

async function reloadTree() {
  try {
    const res = await fetch("/api/fs/tree");
    if (!res.ok) throw new Error("Failed to load tree");
    const data = await res.json();
    state.treeData = data;
    renderDirectoryTree(data);
    populateFolderSelects(data);
  } catch (err) {
    showToast("Error loading directory tree: " + err.message, "error");
  }
}

function renderDirectoryTree(rootNode) {
  dom.directoryTreeContainer.innerHTML = "";

  function createNodeElement(node, depth = 0) {
    const container = document.createElement("div");
    container.className = "flex flex-col select-none";

    const isCurrent = state.currentPath === node.path;
    const hasChildren = node.children && node.children.length > 0;

    const row = document.createElement("div");
    row.className = `group flex items-center justify-between px-2 py-1.5 rounded-lg cursor-pointer transition-colors text-xs font-mono ${
      isCurrent
        ? "bg-teal-50 text-primary font-bold border border-teal-200/80"
        : "text-slate-700 hover:bg-slate-100"
    }`;
    row.style.paddingLeft = `${Math.max(8, depth * 16 + 8)}px`;

    // Left side: icon and folder name
    const left = document.createElement("div");
    left.className = "flex items-center gap-1.5 min-w-0";

    const icon = document.createElement("span");
    icon.className = "material-symbols-outlined text-[16px] text-primary flex-shrink-0";
    icon.textContent = isCurrent ? "folder_open" : "folder";
    left.appendChild(icon);

    const label = document.createElement("span");
    label.className = "truncate";
    label.textContent = node.name;
    left.appendChild(label);
    row.appendChild(left);

    // Right side: audio count badge & quick add subfolder button
    const right = document.createElement("div");
    right.className = "flex items-center gap-1 flex-shrink-0";

    if (node.audio_count > 0) {
      const badge = document.createElement("span");
      badge.className = "px-1.5 py-0.2 rounded bg-slate-200/70 text-[10px] text-slate-600 font-semibold";
      badge.textContent = node.audio_count;
      right.appendChild(badge);
    }

    const btnAddSub = document.createElement("button");
    btnAddSub.className = "opacity-0 group-hover:opacity-100 p-0.5 rounded text-slate-400 hover:text-primary transition-opacity";
    btnAddSub.title = "Create Subdirectory";
    btnAddSub.innerHTML = '<span class="material-symbols-outlined text-[14px]">add</span>';
    btnAddSub.addEventListener("click", (e) => {
      e.stopPropagation();
      openModal("modalNewFolder", { parentPath: node.path });
    });
    right.appendChild(btnAddSub);

    row.appendChild(right);

    row.addEventListener("click", () => {
      navigateToFolder(node.path);
    });

    container.appendChild(row);

    if (hasChildren) {
      const childrenWrapper = document.createElement("div");
      childrenWrapper.className = "flex flex-col";
      node.children.forEach(child => {
        childrenWrapper.appendChild(createNodeElement(child, depth + 1));
      });
      container.appendChild(childrenWrapper);
    }

    return container;
  }

  dom.directoryTreeContainer.appendChild(createNodeElement(rootNode, 0));
}

function populateFolderSelects(rootNode) {
  const options = [{ name: "Music Library (Root)", path: "" }];

  function collect(node) {
    if (node.path) {
      options.push({ name: node.path, path: node.path });
    }
    if (node.children) {
      node.children.forEach(collect);
    }
  }
  collect(rootNode);

  // Target select for uploads
  dom.uploadTargetFolderSelect.innerHTML = options
    .map(o => `<option value="${escapeHtml(o.path)}">${escapeHtml(o.name)}</option>`)
    .join("");

  // Target select for move modal
  const moveSelect = document.getElementById("moveTargetSelect");
  if (moveSelect) {
    moveSelect.innerHTML = options
      .map(o => `<option value="${escapeHtml(o.path)}">${escapeHtml(o.name)}</option>`)
      .join("");
  }
}

async function navigateToFolder(relPath) {
  state.currentPath = relPath;
  state.selectedPaths.clear();
  updateSelectionUI();

  try {
    const res = await fetch(`/api/fs/ls?path=${encodeURIComponent(relPath)}`);
    if (!res.ok) throw new Error("Directory not accessible");
    const data = await res.json();
    state.currentListing = data;

    renderBreadcrumbs(data.breadcrumbs);
    renderFolderHeader(data);
    applyFileFilters();
    renderDirectoryTree(state.treeData);

    // Update parent folder button
    if (data.parent_path !== null) {
      dom.btnParentFolder.classList.remove("hidden");
    } else {
      dom.btnParentFolder.classList.add("hidden");
    }

    if (state.activeView !== "explorer") {
      switchView("explorer");
    }
  } catch (err) {
    showToast("Error reading directory: " + err.message, "error");
  }
}

function renderBreadcrumbs(crumbs) {
  // Top header breadcrumbs
  dom.headerBreadcrumbs.innerHTML = crumbs
    .map((c, i) => {
      const isLast = i === crumbs.length - 1;
      return `<span class="${isLast ? "text-slate-900 font-semibold" : "hover:text-primary transition-colors cursor-pointer"}" onclick="navigateToFolder('${escapeJs(c.path)}')">${escapeHtml(c.name)}</span>`;
    })
    .join('<span>/</span>');

  // Command bar breadcrumbs
  dom.explorerBreadcrumbs.innerHTML = `
    <span class="material-symbols-outlined text-primary text-[18px]">dns</span>
    ${crumbs
      .map((c, i) => {
        const isLast = i === crumbs.length - 1;
        if (isLast) {
          return `<span class="px-2 py-0.5 rounded bg-teal-50 border border-teal-200 text-primary font-semibold">${escapeHtml(c.name)}</span>`;
        }
        return `<span class="hover:text-primary transition-colors cursor-pointer" onclick="navigateToFolder('${escapeJs(c.path)}')">${escapeHtml(c.name)}</span><span class="text-slate-300">/</span>`;
      })
      .join("")}
  `;
}

function renderFolderHeader(data) {
  const currentCrumb = data.breadcrumbs[data.breadcrumbs.length - 1];
  dom.currentFolderTitle.textContent = currentCrumb ? currentCrumb.name : "Music Library";
  dom.currentFolderStats.textContent = `${data.total_directories} Directories • ${data.total_files} Files`;
}

function applyFileFilters() {
  if (!state.currentListing) return;

  let files = [...state.currentListing.files];

  // Format filter
  if (state.activeFormatFilter !== "ALL") {
    const ext = state.activeFormatFilter.toLowerCase();
    files = files.filter(f => f.extension.toLowerCase() === ext);
  }

  // Search filter
  if (state.searchQuery) {
    const q = state.searchQuery;
    files = files.filter(f => {
      return (
        f.name.toLowerCase().includes(q) ||
        (f.title && f.title.toLowerCase().includes(q)) ||
        (f.artist && f.artist.toLowerCase().includes(q)) ||
        (f.album && f.album.toLowerCase().includes(q))
      );
    });
  }

  state.filteredFiles = files;
  renderFileList();
}

function renderFileList() {
  const tbody = dom.fileTableBody;
  tbody.innerHTML = "";

  const directories = state.currentListing?.directories || [];
  const files = state.filteredFiles;

  if (directories.length === 0 && files.length === 0) {
    dom.emptyFolderState.classList.remove("hidden");
    return;
  } else {
    dom.emptyFolderState.classList.add("hidden");
  }

  // Render Subdirectories first
  directories.forEach(dir => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50/80 transition-colors group cursor-pointer";
    tr.innerHTML = `
      <td class="p-3 text-center" onclick="event.stopPropagation()">
        <span class="material-symbols-outlined text-slate-300 text-[18px]">folder</span>
      </td>
      <td class="p-3 text-center text-slate-400">--</td>
      <td class="p-3 text-center text-slate-300">
        <span class="material-symbols-outlined text-[20px] text-teal-600">folder</span>
      </td>
      <td class="p-3 font-semibold text-slate-900 flex items-center gap-1.5" colspan="3">
        <span>${escapeHtml(dir.name)}</span>
        <span class="px-1.5 py-0.5 rounded bg-slate-100 text-[10px] text-slate-500 font-mono">${dir.item_count} items</span>
      </td>
      <td class="p-3 font-mono text-slate-400 text-xs">Directory</td>
      <td class="p-3 text-right text-slate-400 font-mono">--</td>
      <td class="p-3 text-center" onclick="event.stopPropagation()">
        <div class="flex items-center justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onclick="openRenameModal('${escapeJs(dir.path)}', '${escapeJs(dir.name)}')" class="p-1 rounded text-slate-500 hover:text-primary hover:bg-slate-100" title="Rename Directory">
            <span class="material-symbols-outlined text-[16px]">drive_file_rename_outline</span>
          </button>
          <button onclick="openMoveModal(['${escapeJs(dir.path)}'])" class="p-1 rounded text-slate-500 hover:text-primary hover:bg-slate-100" title="Move Directory">
            <span class="material-symbols-outlined text-[16px]">drive_file_move</span>
          </button>
          <button onclick="openDeleteModal(['${escapeJs(dir.path)}'])" class="p-1 rounded text-slate-500 hover:text-rose-600 hover:bg-rose-50" title="Delete Directory">
            <span class="material-symbols-outlined text-[16px]">delete</span>
          </button>
        </div>
      </td>
    `;
    tr.addEventListener("click", () => navigateToFolder(dir.path));
    tbody.appendChild(tr);
  });

  // Render Files
  files.forEach(file => {
    const isSelected = state.selectedPaths.has(file.path);
    const isPlayingThis = state.isPlaying && state.playingPath === file.path;

    const tr = document.createElement("tr");
    tr.className = `hover:bg-teal-50/40 transition-colors group ${isSelected ? "bg-teal-50/60" : ""}`;

    // Play icon
    const playIconName = isPlayingThis ? "pause" : "play_arrow";

    // Duration format
    const durationStr = file.duration ? formatDuration(file.duration) : "--:--";

    // Tech Specs string
    const formatUpper = file.extension.replace(".", "").toUpperCase();
    const specsStr = file.bitrate ? `${Math.round(file.bitrate / 1000)}k` : "";

    tr.innerHTML = `
      <td class="p-3 text-center" onclick="event.stopPropagation()">
        <input type="checkbox" class="file-checkbox accent-teal-600 rounded cursor-pointer" data-path="${escapeHtml(file.path)}" ${isSelected ? "checked" : ""} />
      </td>
      <td class="p-3 text-center">
        <button onclick="playTrackInline('${escapeJs(file.path)}')" class="w-7 h-7 rounded-lg ${isPlayingThis ? "bg-primary text-white" : "bg-slate-100 hover:bg-teal-100 text-slate-700 hover:text-primary"} flex items-center justify-center transition-colors shadow-xs" title="${isPlayingThis ? 'Pause' : 'Play'}">
          <span class="material-symbols-outlined text-[18px]">${playIconName}</span>
        </button>
      </td>
      <td class="p-3 text-center">
        <div class="w-8 h-8 rounded-lg overflow-hidden bg-slate-100 border border-slate-200/80 flex items-center justify-center shadow-2xs">
          ${file.has_cover 
            ? `<img src="/api/audio/artwork?path=${encodeURIComponent(file.path)}" class="w-full h-full object-cover" loading="lazy" />`
            : `<span class="material-symbols-outlined text-[16px] text-slate-400">album</span>`
          }
        </div>
      </td>
      <td class="p-3">
        <div class="flex flex-col">
          <div class="font-semibold text-slate-900 group-hover:text-primary transition-colors cursor-pointer" onclick="openTagEditor('${escapeJs(file.path)}')">
            ${escapeHtml(file.title || file.name)}
          </div>
          <div class="text-[11px] text-slate-500 font-mono truncate max-w-xs">${escapeHtml(file.name)}</div>
        </div>
      </td>
      <td class="p-3 text-slate-700 font-medium">${escapeHtml(file.artist || "--")}</td>
      <td class="p-3 text-slate-600">${escapeHtml(file.album || "--")}</td>
      <td class="p-3">
        <span class="px-2 py-0.5 rounded bg-slate-100 border border-slate-200 text-slate-700 font-mono text-[10px] font-semibold">
          ${formatUpper} ${specsStr ? "• " + specsStr : ""}
        </span>
      </td>
      <td class="p-3 text-right font-mono text-slate-600">${durationStr}</td>
      <td class="p-3 text-center" onclick="event.stopPropagation()">
        <div class="flex items-center justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onclick="openTagEditor('${escapeJs(file.path)}')" class="p-1 rounded text-slate-500 hover:text-primary hover:bg-slate-100" title="Edit Metadata">
            <span class="material-symbols-outlined text-[16px]">edit</span>
          </button>
          <button onclick="openRenameModal('${escapeJs(file.path)}', '${escapeJs(file.name)}')" class="p-1 rounded text-slate-500 hover:text-primary hover:bg-slate-100" title="Rename File">
            <span class="material-symbols-outlined text-[16px]">drive_file_rename_outline</span>
          </button>
          <button onclick="openMoveModal(['${escapeJs(file.path)}'])" class="p-1 rounded text-slate-500 hover:text-primary hover:bg-slate-100" title="Move File">
            <span class="material-symbols-outlined text-[16px]">drive_file_move</span>
          </button>
          <button onclick="openDeleteModal(['${escapeJs(file.path)}'])" class="p-1 rounded text-slate-500 hover:text-rose-600 hover:bg-rose-50" title="Delete File">
            <span class="material-symbols-outlined text-[16px]">delete</span>
          </button>
        </div>
      </td>
    `;

    // Row selection listener
    const checkbox = tr.querySelector(".file-checkbox");
    checkbox.addEventListener("change", (e) => {
      const p = e.target.getAttribute("data-path");
      if (e.target.checked) {
        state.selectedPaths.add(p);
      } else {
        state.selectedPaths.delete(p);
      }
      updateSelectionUI();
      tr.classList.toggle("bg-teal-50/60", e.target.checked);
    });

    tbody.appendChild(tr);
  });
}

function updateSelectionUI() {
  const count = state.selectedPaths.size;
  dom.selectedCount.textContent = count;
  dom.selectionActions.classList.toggle("hidden", count === 0);
  dom.selectionActions.classList.toggle("flex", count > 0);

  // Update master checkbox
  const total = state.filteredFiles.length;
  dom.selectAllCheckbox.checked = total > 0 && count === total;
}

// ==========================================================================
// Deep Metadata Tag Editor & Inspector
// ==========================================================================

async function openTagEditor(filePath) {
  state.editorTrackPath = filePath;
  switchView("editor");

  try {
    const res = await fetch(`/api/audio/metadata?path=${encodeURIComponent(filePath)}`);
    if (!res.ok) throw new Error("Could not read metadata");
    const data = await res.json();
    state.editorOriginalData = JSON.parse(JSON.stringify(data));

    // Populate Track Switcher with all audio files in the current listing
    populateEditorTrackSwitcher(filePath);

    // Populate metadata inputs
    dom.metaTitle.value = data.title || "";
    dom.metaArtist.value = data.artist || "";
    dom.metaAlbumArtist.value = data.album_artist || "";
    dom.metaAlbum.value = data.album || "";
    dom.metaYear.value = data.year || "";
    dom.metaTrackNumber.value = data.track_number || "";
    dom.metaTrackTotal.value = data.track_total || "";
    dom.metaDiscNumber.value = data.disc_number || "";
    dom.metaDiscTotal.value = data.disc_total || "";
    dom.metaGenre.value = data.genre || "";
    dom.metaComposer.value = data.composer || "";
    dom.metaComment.value = data.comment || "";

    // Track position header
    const trk = data.track_number ? `TRACK ${data.track_number.padStart(2, '0')}` : "TRACK --";
    dom.editorTrackPosition.textContent = trk;
    dom.editorFormatTag.textContent = data.codec;

    // Artwork
    renderArtworkPreview(data);

    // Acoustic Specs
    renderAcousticSpecs(data);

    // Reset modified state
    state.editorModified = false;
    dom.unsavedChangesBadge.classList.add("hidden");

    // Load waveform & audio player
    loadAudioTrack(filePath, data);

  } catch (err) {
    showToast("Error loading track: " + err.message, "error");
  }
}

function populateEditorTrackSwitcher(selectedPath) {
  const audioTracks = state.currentListing?.files?.filter(f => f.is_audio) || [];
  state.editorDirTracks = audioTracks;

  dom.editorTrackSwitcher.innerHTML = audioTracks
    .map(t => `<option value="${escapeHtml(t.path)}" ${t.path === selectedPath ? "selected" : ""}>${escapeHtml(t.title || t.name)}</option>`)
    .join("");
}

function renderArtworkPreview(data) {
  if (data.has_cover) {
    dom.editorArtworkImg.src = `/api/audio/artwork?path=${encodeURIComponent(data.path)}&t=${Date.now()}`;
    dom.editorArtworkImg.classList.remove("hidden");
    dom.artworkPlaceholder.classList.add("hidden");
    dom.artworkSpecPill.textContent = "EMBEDDED";

    if (data.artwork_info) {
      dom.artworkFormat.textContent = data.artwork_info.format;
      dom.artworkDimensions.textContent = `${data.artwork_info.width}x${data.artwork_info.height}`;
      dom.artworkSize.textContent = data.artwork_info.size_str;
    }
  } else {
    dom.editorArtworkImg.classList.add("hidden");
    dom.artworkPlaceholder.classList.remove("hidden");
    dom.artworkSpecPill.textContent = "NO ARTWORK";
    dom.artworkFormat.textContent = "--";
    dom.artworkDimensions.textContent = "--";
    dom.artworkSize.textContent = "--";
  }
}

function renderAcousticSpecs(data) {
  dom.specBitrate.innerHTML = `${Math.round(data.bitrate / 1000) || "--"} <span class="font-mono text-xs text-slate-500 font-normal">kbps</span>`;
  dom.specSampleRate.innerHTML = `${(data.sample_rate / 1000).toFixed(1) || "--"} <span class="font-mono text-xs text-slate-500 font-normal">kHz</span>`;
  dom.specBitDepth.innerHTML = `${data.bit_depth || "16"} <span class="font-mono text-xs text-slate-500 font-normal">bit</span>`;
  dom.specChannels.textContent = data.channel_mode;
  dom.specCodec.textContent = `CODEC: ${data.codec}`;
  dom.specFileSize.textContent = `SIZE: ${data.file_size_str}`;

  const isLossless = data.extension === ".flac" || data.extension === ".wav";
  dom.specLosslessPill.textContent = isLossless ? "LOSSLESS MASTER" : "COMPRESSED AUDIO";
  dom.playerCodecBadge.textContent = `${data.bit_depth || 16}-bit / ${(data.sample_rate / 1000).toFixed(1)} kHz`;
}

function checkEditorDirty() {
  if (!state.editorOriginalData) return;

  const current = {
    title: dom.metaTitle.value.trim(),
    artist: dom.metaArtist.value.trim(),
    album_artist: dom.metaAlbumArtist.value.trim(),
    album: dom.metaAlbum.value.trim(),
    year: dom.metaYear.value.trim(),
    track_number: dom.metaTrackNumber.value.trim(),
    track_total: dom.metaTrackTotal.value.trim(),
    disc_number: dom.metaDiscNumber.value.trim(),
    disc_total: dom.metaDiscTotal.value.trim(),
    genre: dom.metaGenre.value.trim(),
    composer: dom.metaComposer.value.trim(),
    comment: dom.metaComment.value.trim(),
  };

  const orig = state.editorOriginalData;
  let changes = 0;
  for (const k in current) {
    if (current[k] !== (orig[k] || "")) {
      changes++;
    }
  }

  state.editorModified = changes > 0;
  if (state.editorModified) {
    dom.unsavedChangesBadge.classList.remove("hidden");
    dom.unsavedCount.textContent = `${changes} MODIFICATION${changes > 1 ? "S" : ""}`;
  } else {
    dom.unsavedChangesBadge.classList.add("hidden");
  }
}

async function handleSaveTags() {
  if (!state.editorTrackPath) return;

  const payload = {
    path: state.editorTrackPath,
    title: dom.metaTitle.value.trim(),
    artist: dom.metaArtist.value.trim(),
    album_artist: dom.metaAlbumArtist.value.trim(),
    album: dom.metaAlbum.value.trim(),
    year: dom.metaYear.value.trim(),
    track_number: dom.metaTrackNumber.value.trim(),
    track_total: dom.metaTrackTotal.value.trim(),
    disc_number: dom.metaDiscNumber.value.trim(),
    disc_total: dom.metaDiscTotal.value.trim(),
    genre: dom.metaGenre.value.trim(),
    composer: dom.metaComposer.value.trim(),
    comment: dom.metaComment.value.trim(),
  };

  try {
    const res = await fetch("/api/audio/metadata", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Save failed");
    const updated = await res.json();
    state.editorOriginalData = JSON.parse(JSON.stringify(updated));
    checkEditorDirty();
    showToast("Metadata saved successfully", "success");

    // Refresh directory file list
    if (state.currentListing) {
      const idx = state.currentListing.files.findIndex(f => f.path === state.editorTrackPath);
      if (idx !== -1) {
        state.currentListing.files[idx].title = updated.title;
        state.currentListing.files[idx].artist = updated.artist;
        state.currentListing.files[idx].album = updated.album;
        state.currentListing.files[idx].track_number = updated.track_number;
        applyFileFilters();
      }
    }
  } catch (err) {
    showToast("Failed to save metadata: " + err.message, "error");
  }
}

function handleRevertTags() {
  if (!state.editorOriginalData) return;
  const o = state.editorOriginalData;
  dom.metaTitle.value = o.title || "";
  dom.metaArtist.value = o.artist || "";
  dom.metaAlbumArtist.value = o.album_artist || "";
  dom.metaAlbum.value = o.album || "";
  dom.metaYear.value = o.year || "";
  dom.metaTrackNumber.value = o.track_number || "";
  dom.metaTrackTotal.value = o.track_total || "";
  dom.metaDiscNumber.value = o.disc_number || "";
  dom.metaDiscTotal.value = o.disc_total || "";
  dom.metaGenre.value = o.genre || "";
  dom.metaComposer.value = o.composer || "";
  dom.metaComment.value = o.comment || "";
  checkEditorDirty();
  showToast("Reverted modifications", "info");
}

async function handleArtworkUpload(e) {
  const file = e.target.files[0];
  if (!file || !state.editorTrackPath) return;

  const formData = new FormData();
  formData.append("path", state.editorTrackPath);
  formData.append("file", file);

  try {
    const res = await fetch("/api/audio/artwork", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Artwork upload failed");
    showToast("Cover art embedded successfully", "success");
    // Reload metadata
    openTagEditor(state.editorTrackPath);
  } catch (err) {
    showToast("Error uploading cover art: " + err.message, "error");
  }
}

async function handleRemoveArtwork() {
  if (!state.editorTrackPath) return;
  if (!confirm("Are you sure you want to remove the embedded cover artwork?")) return;

  try {
    const res = await fetch(`/api/audio/artwork?path=${encodeURIComponent(state.editorTrackPath)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Removal failed");
    showToast("Artwork removed", "info");
    openTagEditor(state.editorTrackPath);
  } catch (err) {
    showToast("Error removing artwork: " + err.message, "error");
  }
}

// ==========================================================================
// Studio Audio Player & Waveform Visualizer
// ==========================================================================

async function loadAudioTrack(filePath, metaData) {
  const audio = dom.globalAudioPlayer;
  const isCurrentlyPlayingThis = state.playingPath === filePath && state.isPlaying;

  if (state.playingPath !== filePath) {
    state.playingPath = filePath;
    audio.src = `/api/audio/stream?path=${encodeURIComponent(filePath)}`;
    audio.load();
  }

  dom.playerTotalTime.textContent = metaData.duration_str || "00:00";
  dom.playerCurrentTime.textContent = "00:00";

  // Fetch waveform peaks
  try {
    const res = await fetch(`/api/audio/waveform?path=${encodeURIComponent(filePath)}`);
    if (res.ok) {
      const wData = await res.json();
      state.waveformPeaks = wData.peaks;
      renderWaveformBars(wData.peaks);
    }
  } catch (err) {
    state.waveformPeaks = new Array(120).fill(0.3);
    renderWaveformBars(state.waveformPeaks);
  }
}

function renderWaveformBars(peaks) {
  dom.waveformBars.innerHTML = "";
  peaks.forEach((peak, i) => {
    const bar = document.createElement("div");
    bar.className = "waveform-bar flex-1 rounded-full bg-slate-300";
    bar.style.height = `${Math.max(10, Math.round(peak * 100))}%`;
    bar.setAttribute("data-index", i);
    dom.waveformBars.appendChild(bar);
  });
  updateWaveformDisplay(0);
}

function updateWaveformDisplay(progressRatio) {
  const bars = dom.waveformBars.children;
  const threshold = Math.floor(progressRatio * bars.length);
  for (let i = 0; i < bars.length; i++) {
    if (i <= threshold) {
      bars[i].className = "waveform-bar flex-1 rounded-full bg-primary";
    } else {
      bars[i].className = "waveform-bar flex-1 rounded-full bg-slate-300";
    }
  }
  dom.waveformPlayhead.style.left = `${progressRatio * 100}%`;
}

function toggleAudioPlayback() {
  const audio = dom.globalAudioPlayer;
  if (!audio.src) return;

  if (audio.paused) {
    audio.play();
    state.isPlaying = true;
    dom.playerPlayIcon.textContent = "pause";
  } else {
    audio.pause();
    state.isPlaying = false;
    dom.playerPlayIcon.textContent = "play_arrow";
  }
  renderFileList();
}

function playTrackInline(filePath) {
  if (state.playingPath === filePath && state.isPlaying) {
    dom.globalAudioPlayer.pause();
    state.isPlaying = false;
    dom.playerPlayIcon.textContent = "play_arrow";
  } else {
    state.playingPath = filePath;
    dom.globalAudioPlayer.src = `/api/audio/stream?path=${encodeURIComponent(filePath)}`;
    dom.globalAudioPlayer.play();
    state.isPlaying = true;
    dom.playerPlayIcon.textContent = "pause";
  }
  renderFileList();
}

function onAudioLoaded() {
  const dur = dom.globalAudioPlayer.duration;
  if (!isNaN(dur)) {
    dom.playerTotalTime.textContent = formatDuration(dur);
  }
}

function updatePlayerProgress() {
  const cur = dom.globalAudioPlayer.currentTime;
  const dur = dom.globalAudioPlayer.duration;
  dom.playerCurrentTime.textContent = formatDuration(cur);

  if (!isNaN(dur) && dur > 0) {
    const ratio = cur / dur;
    updateWaveformDisplay(ratio);
  }
}

function handleWaveformSeek(e) {
  const rect = dom.waveformContainer.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const ratio = Math.max(0, Math.min(1, clickX / rect.width));

  if (!isNaN(dom.globalAudioPlayer.duration)) {
    dom.globalAudioPlayer.currentTime = ratio * dom.globalAudioPlayer.duration;
    updateWaveformDisplay(ratio);
  }
}

// ==========================================================================
// Filesystem Operations: Modals & Handlers
// ==========================================================================

function openModal(id, opts = {}) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove("hidden");

  if (id === "modalNewFolder") {
    document.getElementById("newFolderNameInput").value = "";
    document.getElementById("newFolderNameInput").focus();
  }
}

function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("hidden");
}

async function handleCreateFolder(e) {
  e.preventDefault();
  const name = document.getElementById("newFolderNameInput").value.trim();
  if (!name) return;

  try {
    const res = await fetch("/api/fs/mkdir", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parent_path: state.currentPath, name }),
    });

    if (!res.ok) throw new Error("Directory creation failed");
    closeModal("modalNewFolder");
    showToast(`Directory "${name}" created`, "success");
    reloadTree();
    navigateToFolder(state.currentPath);
  } catch (err) {
    showToast("Error creating directory: " + err.message, "error");
  }
}

function openRenameModal(path, currentName) {
  document.getElementById("renameSourcePath").value = path;
  document.getElementById("renameNewNameInput").value = currentName;
  openModal("modalRename");
  document.getElementById("renameNewNameInput").focus();
}

async function handleRenameSubmit(e) {
  e.preventDefault();
  const path = document.getElementById("renameSourcePath").value;
  const new_name = document.getElementById("renameNewNameInput").value.trim();
  if (!new_name) return;

  try {
    const res = await fetch("/api/fs/rename", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, new_name }),
    });

    if (!res.ok) throw new Error("Rename failed");
    closeModal("modalRename");
    showToast("Item renamed successfully", "success");
    reloadTree();
    navigateToFolder(state.currentPath);
  } catch (err) {
    showToast("Error renaming: " + err.message, "error");
  }
}

let pendingMovePaths = [];
function openMoveModal(paths) {
  if (!paths || paths.length === 0) return;
  pendingMovePaths = paths;
  document.getElementById("moveSummaryText").textContent = `Move ${paths.length} item(s) to:`;
  openModal("modalMove");
}

async function handleMoveSubmit(e) {
  e.preventDefault();
  const target_dir = document.getElementById("moveTargetSelect").value;

  try {
    const res = await fetch("/api/fs/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paths: pendingMovePaths, target_dir }),
    });

    if (!res.ok) throw new Error("Move failed");
    const data = await res.json();
    closeModal("modalMove");
    showToast(`Moved ${data.moved.length} item(s)`, "success");
    reloadTree();
    navigateToFolder(state.currentPath);
  } catch (err) {
    showToast("Error moving items: " + err.message, "error");
  }
}

let pendingDeletePaths = [];
function openDeleteModal(paths) {
  if (!paths || paths.length === 0) return;
  pendingDeletePaths = paths;
  document.getElementById("deleteConfirmMessage").textContent = `Are you sure you want to permanently delete ${paths.length} item(s)?`;
  openModal("modalDelete");
}

async function handleConfirmDelete() {
  try {
    const res = await fetch("/api/fs/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ paths: pendingDeletePaths }),
    });

    if (!res.ok) throw new Error("Deletion failed");
    closeModal("modalDelete");
    showToast(`Deleted ${pendingDeletePaths.length} item(s)`, "info");
    reloadTree();
    navigateToFolder(state.currentPath);
  } catch (err) {
    showToast("Error deleting: " + err.message, "error");
  }
}

function openBatchTagModal() {
  const count = state.selectedPaths.size;
  if (count === 0) return;
  document.getElementById("batchTagCountText").textContent = `Editing ${count} track(s)`;
  openModal("modalBatchTag");
}

async function handleBatchTagSubmit(e) {
  e.preventDefault();
  const paths = Array.from(state.selectedPaths);
  const payload = {
    paths,
    artist: document.getElementById("batchArtist").value.trim() || null,
    album_artist: document.getElementById("batchAlbumArtist").value.trim() || null,
    album: document.getElementById("batchAlbum").value.trim() || null,
    year: document.getElementById("batchYear").value.trim() || null,
    genre: document.getElementById("batchGenre").value.trim() || null,
    composer: document.getElementById("batchComposer").value.trim() || null,
  };

  try {
    const res = await fetch("/api/audio/batch-metadata", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Batch tagging failed");
    const data = await res.json();
    closeModal("modalBatchTag");
    showToast(`Batch updated ${data.updated.length} tracks`, "success");
    navigateToFolder(state.currentPath);
  } catch (err) {
    showToast("Error during batch tagging: " + err.message, "error");
  }
}

// ==========================================================================
// Audio Ingestion & File Upload Queue
// ==========================================================================

function addFilesToUploadQueue(files) {
  const targetDir = dom.uploadTargetFolderSelect.value;
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    state.uploadQueue.push({
      id: "upl_" + Math.random().toString(36).substring(2, 9),
      file,
      targetDir,
      status: "READY",
      progress: 0,
      error: null,
    });
  }
  updateQueueUI();
  switchView("uploads");
  showToast(`Added ${files.length} file(s) to upload queue`, "info");
}

function updateQueueUI() {
  const q = state.uploadQueue;
  dom.queueCountBadge.textContent = `${q.length} file${q.length === 1 ? "" : "s"}`;
  dom.uploadBadge.classList.toggle("hidden", q.length === 0);

  const tbody = dom.queueTableBody;
  tbody.innerHTML = "";

  if (q.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="p-8 text-center text-on-surface-muted font-mono">Queue is empty. Drop files above to begin ingestion.</td></tr>`;
    return;
  }

  q.forEach(item => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50/70 font-mono text-xs";

    let statusPillClass = "bg-slate-100 text-slate-700";
    if (item.status === "UPLOADING") statusPillClass = "bg-teal-50 text-primary animate-pulse";
    if (item.status === "COMPLETE") statusPillClass = "bg-emerald-50 text-emerald-700 font-bold";
    if (item.status === "FAILED") statusPillClass = "bg-rose-50 text-rose-700 font-bold";

    tr.innerHTML = `
      <td class="p-3 font-semibold text-slate-900">${escapeHtml(item.file.name)}</td>
      <td class="p-3 text-slate-500">${formatFileSize(item.file.size)}</td>
      <td class="p-3 text-slate-600">${escapeHtml(item.targetDir || "Library (Root)")}</td>
      <td class="p-3">
        <span class="px-2 py-0.5 rounded ${statusPillClass}">${item.status}</span>
      </td>
      <td class="p-3 text-center">
        <button onclick="removeQueueItem('${item.id}')" class="p-1 rounded text-slate-400 hover:text-rose-600">
          <span class="material-symbols-outlined text-[16px]">close</span>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function removeQueueItem(id) {
  state.uploadQueue = state.uploadQueue.filter(i => i.id !== id);
  updateQueueUI();
}

function clearUploadQueue() {
  state.uploadQueue = [];
  updateQueueUI();
}

async function startBatchUpload() {
  if (state.isUploading || state.uploadQueue.length === 0) return;
  state.isUploading = true;

  // Group by target folder
  const byFolder = {};
  state.uploadQueue.forEach(item => {
    if (item.status !== "COMPLETE") {
      byFolder[item.targetDir] = byFolder[item.targetDir] || [];
      byFolder[item.targetDir].push(item);
    }
  });

  for (const targetDir in byFolder) {
    const items = byFolder[targetDir];
    items.forEach(i => i.status = "UPLOADING");
    updateQueueUI();

    const formData = new FormData();
    formData.append("target_dir", targetDir);
    items.forEach(i => formData.append("files", i.file));

    try {
      const res = await fetch("/api/fs/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error("Upload request failed");
      items.forEach(i => i.status = "COMPLETE");
      updateQueueUI();
      showToast(`Uploaded ${items.length} file(s)`, "success");
    } catch (err) {
      items.forEach(i => {
        i.status = "FAILED";
        i.error = err.message;
      });
      updateQueueUI();
      showToast("Upload error: " + err.message, "error");
    }
  }

  state.isUploading = false;
  reloadTree();
  navigateToFolder(state.currentPath);
}

// ==========================================================================
// Utilities & Toast Notifications
// ==========================================================================

function formatDuration(sec) {
  if (isNaN(sec) || sec <= 0) return "00:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function formatFileSize(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function showToast(message, type = "info") {
  const toast = document.createElement("div");
  const bgMap = {
    success: "bg-teal-900/95 border-teal-500/50 text-white",
    error: "bg-rose-900/95 border-rose-500/50 text-white",
    info: "bg-slate-900/95 border-slate-700/50 text-white",
  };
  const iconMap = {
    success: "check_circle",
    error: "error",
    info: "info",
  };

  toast.className = `pointer-events-auto flex items-center gap-2.5 px-4 py-2.5 rounded-xl border shadow-xl text-xs font-mono transition-all transform duration-300 translate-y-2 opacity-0 ${bgMap[type] || bgMap.info}`;
  toast.innerHTML = `
    <span class="material-symbols-outlined text-[18px] text-teal-400">${iconMap[type] || "info"}</span>
    <span>${escapeHtml(message)}</span>
  `;

  dom.toastContainer.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.remove("translate-y-2", "opacity-0");
  });

  setTimeout(() => {
    toast.classList.add("translate-y-2", "opacity-0");
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function escapeJs(str) {
  if (!str) return "";
  return String(str).replace(/\\/g, "\\\\").replace(/'/g, "\\'");
}
