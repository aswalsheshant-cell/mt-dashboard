// =====================================================================
// PARAMETERS  —  create each of these in Power BI:  Home > Manage Parameters
// =====================================================================
// These are the ONLY things that change between machines. Set pRootFolder
// to wherever you keep the dashboard data folders on YOUR system, then every
// teammate only edits this one value.
//
// Folder layout expected under pRootFolder:
//   <pRootFolder>\RawDataFolders\Primary_Weekly\     <- drop weekly primary files here
//   <pRootFolder>\RawDataFolders\Offtake_Monthly\    <- drop monthly offtake files here
//   <pRootFolder>\RawDataFolders\Nielsen_Monthly\    <- drop monthly Nielsen files here
//   <pRootFolder>\RawDataFolders\TDP_Monthly\        <- drop monthly TDP / ACV files here
//   <pRootFolder>\SeedData\Masters\                  <- master / dimension tables
//   <pRootFolder>\SeedData\Mapping\                  <- store-to-SO mapping
//   <pRootFolder>\SeedData\Targets\                  <- FY targets
// =====================================================================

// ---- Parameter: pRootFolder  (Type = Text) ----
// Example (Windows): "C:\MT-Dashboard"
// Example (OneDrive): "C:\Users\you\OneDrive - Honasa\MT-Dashboard"
"C:\MT-Dashboard" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]
